"""External planner CLI client."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .models import CommandResult, PlannerResult


def run_planner(planner_command: str, request_file: str | Path, matrix_file: str | Path) -> PlannerResult:
    command = planner_command.split() + ["create", "--request-file", str(request_file), "--matrix", str(matrix_file)]
    start = time.monotonic()
    proc = subprocess.run(command, capture_output=True, text=True)
    duration = time.monotonic() - start
    result = CommandResult(command, proc.returncode, proc.stdout, proc.stderr, duration)
    return PlannerResult(result, detect_plan_dir(proc.stdout))


def detect_plan_dir(stdout: str, search_root: str | Path = ".codex-task-planner/plans") -> str | None:
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("plan_dir "):
            return stripped.split(" ", 1)[1].strip()
        if stripped.startswith("plan_dir:"):
            return stripped.split(":", 1)[1].strip()
        if ".codex-task-planner/plans/" in stripped:
            for part in stripped.split():
                if ".codex-task-planner/plans/" in part:
                    return part
    root = Path(search_root)
    if not root.exists():
        return None
    candidates = [path for path in root.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return str(max(candidates, key=lambda path: path.stat().st_mtime))
