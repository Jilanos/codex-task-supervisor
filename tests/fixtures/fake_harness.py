#!/usr/bin/env python3
"""Fake codex-task-harness used by tests."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--task-file", required=True)
    args = parser.parse_args()
    task = json.loads(Path(args.task_file).read_text(encoding="utf-8"))
    task_id = task["task_id"]
    status = "passed"
    if "TASK-002" in task_id:
        status = "blocked"
    if "TASK-003" in task_id:
        status = "failed"
    if os.environ.get("FAKE_HARNESS_STATUS"):
        status = os.environ["FAKE_HARNESS_STATUS"]
    report_dir = Path(task["output_root"]) / "codex_runs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "run_id": task_id,
        "status": status,
        "model": task["model"],
        "reasoning_effort": task["reasoning_effort"],
        "workspace": task["workspace"],
        "duration_seconds": 1.0 + len(task_id) / 100.0,
        "codex_exit_code": 0 if status != "failed" else 1,
        "stdout_path": str(report_dir / f"{task_id}.stdout.txt"),
        "stderr_path": str(report_dir / f"{task_id}.stderr.txt"),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "checks": [
            {
                "command": command,
                "exit_code": 0 if status == "passed" else 1,
                "duration_seconds": 0.1,
                "stdout": "ok" if status == "passed" else "",
                "stderr": "" if status == "passed" else status,
            }
            for command in task.get("checks", [])
        ],
        "changed_files": ["src/example.py"] if "TASK-001" in task_id else [],
        "artifacts": [{"artifact_type": "report", "path": str(report_dir / f"{task_id}.json")}],
    }
    if not os.environ.get("FAKE_HARNESS_NO_TOKENS") and "TASK-002" not in task_id:
        report["token_usage"] = {
            "input_tokens": 100,
            "output_tokens": 50,
            "reasoning_tokens": 25 if task["reasoning_effort"] == "low" else 75,
            "total_tokens": 175 if task["reasoning_effort"] == "low" else 225,
        }
    (report_dir / f"{task_id}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"report_path {report_dir / f'{task_id}.json'}")
    return 0 if status != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
