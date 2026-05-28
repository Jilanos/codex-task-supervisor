"""Typed dataclasses for supervisor state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoringConfig:
    quality_weight: float = 0.6
    cost_weight: float = 0.25
    duration_weight: float = 0.15


@dataclass(frozen=True)
class SupervisorConfig:
    planner_command: str = "codex-task-planner"
    harness_command: str = "codex-task-harness"
    database_path: str = ".codex-task-supervisor/state/supervisor.sqlite3"
    reports_root: str = ".codex-task-supervisor/reports"
    stop_on_first_failure: bool = False
    max_parallel_runs: int = 1
    scoring: ScoringConfig = ScoringConfig()


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


@dataclass(frozen=True)
class PlannerResult:
    command_result: CommandResult
    plan_dir: str | None


@dataclass(frozen=True)
class HarnessResult:
    command_result: CommandResult
    task_file: str
    report_path: str | None
    report: dict[str, Any] | None
    error: str | None = None
