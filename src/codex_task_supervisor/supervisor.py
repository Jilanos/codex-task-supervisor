"""Benchmark orchestration pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from .database import Database
from .harness_client import run_harness
from .models import SupervisorConfig
from .planner_client import run_planner
from .reports import generate_reports
from .scoring import score_plan
from .validation import validate_command, validate_file, validate_plan_dir


class PlannerFailure(RuntimeError):
    """Raised when the external planner fails."""


class HarnessFailure(RuntimeError):
    """Raised when an external harness run fails and fail-fast is enabled."""


class ReportFailure(RuntimeError):
    """Raised when final report generation fails."""


def run_benchmark(request_file: str | Path, matrix_file: str | Path, config: SupervisorConfig) -> str:
    validate_file(request_file, "request file")
    validate_file(matrix_file, "matrix file")
    validate_command(config.planner_command, "planner command")
    validate_command(config.harness_command, "harness command")
    db = Database(config.database_path)
    db.initialize()

    planner = run_planner(config.planner_command, request_file, matrix_file)
    if planner.command_result.exit_code != 0:
        raise PlannerFailure(planner.command_result.stderr or planner.command_result.stdout or "planner failed")
    if not planner.plan_dir:
        raise PlannerFailure("planner did not expose a plan directory")
    plan_id = ingest_plan(planner.plan_dir, config)
    execute_plan(plan_id, config)
    score_plan(db, plan_id, config.scoring)
    try:
        generate_reports(db, plan_id, config.reports_root)
    except Exception as exc:
        raise ReportFailure(str(exc)) from exc
    return plan_id


def ingest_plan(plan_dir: str | Path, config: SupervisorConfig) -> str:
    directory = validate_plan_dir(plan_dir)
    db = Database(config.database_path)
    db.initialize()
    _validate_generated_task_files(directory)
    return db.ingest_plan(directory)


def execute_plan(plan_id: str, config: SupervisorConfig) -> None:
    db = Database(config.database_path)
    db.initialize()
    expected_runs = db.fetch_expected_runs(plan_id)
    for expected in expected_runs:
        result = run_harness(config.harness_command, expected["task_file"])
        if result.report is None:
            report = _failed_report(expected, result.error or "harness report missing", result.command_result.duration_seconds, result.command_result.exit_code)
        else:
            report = result.report
        db.insert_run_report(plan_id, expected, report, result.report_path)
        if config.stop_on_first_failure and report.get("status") != "passed":
            raise HarnessFailure(f"harness run failed: {expected['expected_run_id']}")
    db.update_plan_status(plan_id, "executed")


def score_existing_plan(plan_id: str, config: SupervisorConfig) -> None:
    db = Database(config.database_path)
    score_plan(db, plan_id, config.scoring)


def generate_existing_report(plan_id: str, config: SupervisorConfig) -> tuple[Path, Path]:
    db = Database(config.database_path)
    try:
        return generate_reports(db, plan_id, config.reports_root)
    except Exception as exc:
        raise ReportFailure(str(exc)) from exc


def _validate_generated_task_files(plan_dir: Path) -> None:
    runs = [json.loads(line) for line in (plan_dir / "generated_runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for run in runs:
        task_file = Path(run["task_file"])
        if not task_file.exists():
            raise ValueError(f"generated task file does not exist: {task_file}")


def _failed_report(expected, error: str, duration: float, exit_code: int) -> dict[str, object]:
    return {
        "run_id": expected["expected_run_id"],
        "status": "failed",
        "model": "",
        "reasoning_effort": "",
        "workspace": None,
        "duration_seconds": duration,
        "codex_exit_code": exit_code,
        "checks": [],
        "changed_files": [],
        "artifacts": [{"artifact_type": "error", "path": error}],
    }
