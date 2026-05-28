"""External harness CLI client."""

from __future__ import annotations

import json
import shlex
import subprocess
import time
from pathlib import Path

from .models import CommandResult, HarnessResult
from .validation import validate_report_shape


def run_harness(harness_command: str, task_file: str | Path) -> HarnessResult:
    task_path = Path(task_file)
    command = shlex.split(harness_command) + ["run", "--task-file", str(task_path)]
    start = time.monotonic()
    proc = subprocess.run(command, capture_output=True, text=True)
    duration = time.monotonic() - start
    command_result = CommandResult(command, proc.returncode, proc.stdout, proc.stderr, duration)
    report_path = expected_report_path(task_path)
    if not report_path.exists():
        return HarnessResult(command_result, str(task_path), str(report_path), None, f"missing harness report: {report_path}")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        validate_report_shape(report)
    except (json.JSONDecodeError, ValueError) as exc:
        return HarnessResult(command_result, str(task_path), str(report_path), None, f"invalid harness report: {exc}")
    return HarnessResult(command_result, str(task_path), str(report_path), report)


def expected_report_path(task_file: str | Path) -> Path:
    raw = json.loads(Path(task_file).read_text(encoding="utf-8"))
    return Path(raw["output_root"]) / "codex_runs" / f"{raw['task_id']}.json"
