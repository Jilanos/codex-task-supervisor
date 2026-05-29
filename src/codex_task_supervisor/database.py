"""SQLite persistence without an ORM."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS plans (
        plan_id TEXT PRIMARY KEY,
        request TEXT NOT NULL,
        plan_dir TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,
        task_count INTEGER NOT NULL,
        mode_count INTEGER NOT NULL,
        generated_run_count INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT NOT NULL,
        plan_id TEXT NOT NULL,
        title TEXT NOT NULL,
        task_type TEXT NOT NULL,
        estimated_complexity TEXT NOT NULL,
        dependencies_json TEXT NOT NULL,
        prompt TEXT NOT NULL,
        local_context_json TEXT NOT NULL,
        acceptance_criteria_json TEXT NOT NULL,
        features_json TEXT NOT NULL DEFAULT '{}',
        PRIMARY KEY (plan_id, task_id)
    )""",
    """CREATE TABLE IF NOT EXISTS modes (
        mode_id TEXT NOT NULL,
        plan_id TEXT NOT NULL,
        model TEXT NOT NULL,
        reasoning_effort TEXT NOT NULL,
        timeout_seconds INTEGER NOT NULL,
        PRIMARY KEY (plan_id, mode_id)
    )""",
    """CREATE TABLE IF NOT EXISTS expected_runs (
        expected_run_id TEXT PRIMARY KEY,
        plan_id TEXT NOT NULL,
        task_id TEXT NOT NULL,
        mode_id TEXT NOT NULL,
        task_file TEXT NOT NULL,
        status TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        expected_run_id TEXT NOT NULL,
        plan_id TEXT NOT NULL,
        task_id TEXT NOT NULL,
        mode_id TEXT NOT NULL,
        model TEXT NOT NULL,
        reasoning_effort TEXT NOT NULL,
        status TEXT NOT NULL,
        workspace TEXT,
        duration_seconds REAL,
        codex_exit_code INTEGER,
        stdout_path TEXT,
        stderr_path TEXT,
        report_path TEXT,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS check_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        command TEXT NOT NULL,
        exit_code INTEGER,
        duration_seconds REAL,
        stdout TEXT,
        stderr TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS token_usage (
        run_id TEXT PRIMARY KEY,
        input_tokens INTEGER,
        output_tokens INTEGER,
        reasoning_tokens INTEGER,
        total_tokens INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS changed_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        file_path TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS scores (
        run_id TEXT PRIMARY KEY,
        quality_score REAL NOT NULL,
        cost_score REAL,
        duration_score REAL NOT NULL,
        efficiency_score REAL NOT NULL,
        final_score REAL NOT NULL,
        scoring_notes_json TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        artifact_type TEXT NOT NULL,
        path TEXT NOT NULL
    )""",
]


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        conn = self.connect()
        try:
            for statement in SCHEMA:
                conn.execute(statement)
            # Migrate pre-features databases gracefully
            try:
                conn.execute("ALTER TABLE tasks ADD COLUMN features_json TEXT NOT NULL DEFAULT '{}'")
            except sqlite3.OperationalError:
                pass  # column already exists
            conn.commit()
        finally:
            conn.close()

    def ingest_plan(self, plan_dir: str | Path) -> str:
        directory = Path(plan_dir)
        plan = _read_json(directory / "plan.json")
        tasks = [_loads(line) for line in (directory / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        generated_runs = [_loads(line) for line in (directory / "generated_runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        modes = plan.get("modes", [])
        conn = self.connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO plans VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plan["plan_id"],
                    plan["request"],
                    str(directory),
                    plan["created_at"],
                    "ingested",
                    len(tasks),
                    len(modes),
                    len(generated_runs),
                ),
            )
            for task in tasks:
                conn.execute(
                    "INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        task["task_id"],
                        plan["plan_id"],
                        task["title"],
                        task["task_type"],
                        task["estimated_complexity"],
                        json.dumps(task.get("dependencies", []), sort_keys=True),
                        task["prompt"],
                        json.dumps(task.get("local_context", {}), sort_keys=True),
                        json.dumps(task.get("acceptance_criteria", []), sort_keys=True),
                        json.dumps(task.get("features", {}), sort_keys=True),
                    ),
                )
            for mode in modes:
                conn.execute(
                    "INSERT OR REPLACE INTO modes VALUES (?, ?, ?, ?, ?)",
                    (mode["mode_id"], plan["plan_id"], mode["model"], mode["reasoning_effort"], mode["timeout_seconds"]),
                )
            for run in generated_runs:
                conn.execute(
                    "INSERT OR REPLACE INTO expected_runs VALUES (?, ?, ?, ?, ?, ?)",
                    (run["run_id"], plan["plan_id"], run["task_id"], run["mode_id"], run["task_file"], "pending"),
                )
            conn.commit()
            return plan["plan_id"]
        finally:
            conn.close()

    def insert_run_report(self, plan_id: str, expected: sqlite3.Row, report: dict[str, Any], report_path: str | None) -> None:
        created_at = report.get("created_at") or _now()
        run_id = report.get("run_id") or report.get("task_id") or expected["expected_run_id"]
        conn = self.connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    expected["expected_run_id"],
                    plan_id,
                    expected["task_id"],
                    expected["mode_id"],
                    report.get("model", ""),
                    report.get("reasoning_effort", ""),
                    report.get("status", "failed"),
                    report.get("workspace"),
                    report.get("duration_seconds"),
                    report.get("codex_exit_code"),
                    report.get("stdout_path"),
                    report.get("stderr_path"),
                    report_path,
                    created_at,
                ),
            )
            conn.execute("UPDATE expected_runs SET status = ? WHERE expected_run_id = ?", (report.get("status", "failed"), expected["expected_run_id"]))
            for check in report.get("checks", []):
                conn.execute(
                    "INSERT INTO check_results (run_id, command, exit_code, duration_seconds, stdout, stderr) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        check.get("command", ""),
                        check.get("exit_code"),
                        check.get("duration_seconds"),
                        check.get("stdout"),
                        check.get("stderr"),
                    ),
                )
            usage = report.get("token_usage")
            if isinstance(usage, dict):
                conn.execute(
                    "INSERT OR REPLACE INTO token_usage VALUES (?, ?, ?, ?, ?)",
                    (
                        run_id,
                        usage.get("input_tokens"),
                        usage.get("output_tokens"),
                        usage.get("reasoning_tokens"),
                        usage.get("total_tokens"),
                    ),
                )
            for file_path in report.get("changed_files", []) or []:
                conn.execute("INSERT INTO changed_files (run_id, file_path) VALUES (?, ?)", (run_id, file_path))
            for artifact in report.get("artifacts", []) or []:
                conn.execute(
                    "INSERT INTO artifacts (run_id, artifact_type, path) VALUES (?, ?, ?)",
                    (run_id, artifact.get("artifact_type", "unknown"), artifact.get("path", "")),
                )
            conn.commit()
        finally:
            conn.close()

    def insert_score(self, run_id: str, score: dict[str, Any]) -> None:
        conn = self.connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO scores VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    score["quality_score"],
                    score["cost_score"],
                    score["duration_score"],
                    score["efficiency_score"],
                    score["final_score"],
                    json.dumps(score["scoring_notes"], sort_keys=True),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def fetch_plan(self, plan_id: str) -> sqlite3.Row | None:
        rows = self.fetch_all("SELECT * FROM plans WHERE plan_id = ?", (plan_id,))
        return rows[0] if rows else None

    def fetch_expected_runs(self, plan_id: str) -> list[sqlite3.Row]:
        return self.fetch_all("SELECT * FROM expected_runs WHERE plan_id = ? ORDER BY expected_run_id", (plan_id,))

    def fetch_runs(self, plan_id: str) -> list[sqlite3.Row]:
        return self.fetch_all("SELECT * FROM runs WHERE plan_id = ? ORDER BY run_id", (plan_id,))

    def fetch_run(self, run_id: str) -> sqlite3.Row | None:
        rows = self.fetch_all("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        return rows[0] if rows else None

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        conn = self.connect()
        try:
            return [dict(row) for row in conn.execute(query, params)]
        finally:
            conn.close()

    def fetch_reference_corpus(self) -> list[dict[str, Any]]:
        """Return one entry per (task, model, reasoning_effort) with the best final_score.

        Used by the similarity router to find reference tasks for model recommendation.
        Only includes tasks that have at least one scored run.
        """
        query = """
            SELECT
                t.task_id,
                t.plan_id,
                t.features_json,
                r.model,
                r.reasoning_effort,
                MAX(s.final_score) AS final_score
            FROM tasks t
            JOIN runs r ON r.task_id = t.task_id AND r.plan_id = t.plan_id
            JOIN scores s ON s.run_id = r.run_id
            WHERE s.final_score IS NOT NULL
            GROUP BY t.task_id, t.plan_id, r.model, r.reasoning_effort
            ORDER BY t.plan_id, t.task_id, r.model, r.reasoning_effort
        """
        rows = self.fetch_all(query)
        result = []
        for row in rows:
            features = json.loads(row.get("features_json") or "{}")
            result.append({
                "task_id": row["task_id"],
                "plan_id": row["plan_id"],
                "features": features,
                "model": row["model"],
                "reasoning_effort": row["reasoning_effort"],
                "final_score": row["final_score"],
            })
        return result

    def update_plan_status(self, plan_id: str, status: str) -> None:
        conn = self.connect()
        try:
            conn.execute("UPDATE plans SET status = ? WHERE plan_id = ?", (status, plan_id))
            conn.commit()
        finally:
            conn.close()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _loads(line: str) -> dict[str, Any]:
    return json.loads(line)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
