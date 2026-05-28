"""Validation helpers for files, tools, plans, and harness reports."""

from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    """Raised when user input or generated artifacts are invalid."""


REQUIRED_REPORT_FIELDS = {"run_id", "status", "duration_seconds", "checks"}


def validate_command(command: str, label: str) -> None:
    try:
        first = shlex.split(command)[0]
    except (IndexError, ValueError) as exc:
        raise ValidationError(f"{label} is empty or invalid: {command}") from exc
    path = Path(first)
    if path.exists() and path.is_file() and os.access(path, os.X_OK):
        return
    if shutil.which(first) is not None:
        return
    if path.exists():
        if not path.is_file():
            raise ValidationError(f"{label} is not a file: {first}")
        raise ValidationError(f"{label} is not executable: {first}")
    else:
        raise ValidationError(f"{label} not found on PATH: {first}")


def validate_file(path: str | Path, label: str) -> Path:
    value = Path(path)
    if not value.exists():
        raise ValidationError(f"{label} does not exist: {value}")
    if not value.is_file():
        raise ValidationError(f"{label} is not a file: {value}")
    return value


def validate_plan_dir(plan_dir: str | Path) -> Path:
    directory = Path(plan_dir)
    if not directory.exists() or not directory.is_dir():
        raise ValidationError(f"invalid plan folder: {directory}")
    for name in ["plan.json", "tasks.jsonl", "generated_runs.jsonl"]:
        validate_file(directory / name, name)
    return directory


def validate_task_files(plan_dir: str | Path, generated_runs: list[dict[str, Any]]) -> None:
    for run in generated_runs:
        task_file = run.get("task_file")
        if not task_file:
            raise ValidationError(f"generated run missing task_file: {run}")
        path = Path(task_file)
        if not path.is_absolute():
            path = Path(plan_dir) / path if not str(path).startswith(".codex-task-planner") else Path(task_file)
        if not path.exists():
            raise ValidationError(f"generated task file does not exist: {task_file}")


def validate_report_shape(report: dict[str, Any]) -> None:
    missing = REQUIRED_REPORT_FIELDS - set(report)
    if missing:
        raise ValidationError(f"harness report missing required fields: {', '.join(sorted(missing))}")
    if report["status"] not in {"passed", "failed", "blocked"}:
        raise ValidationError(f"invalid harness report status: {report['status']}")
    if not isinstance(report["checks"], list):
        raise ValidationError("harness report checks must be a list")
