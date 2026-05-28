"""Configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ScoringConfig, SupervisorConfig


class ConfigError(ValueError):
    """Raised for invalid supervisor configuration."""


def load_config(path: str | Path | None = None) -> SupervisorConfig:
    if path is None:
        return SupervisorConfig()
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid config JSON: {exc}") from exc
    return parse_config(raw)


def parse_config(raw: dict[str, Any]) -> SupervisorConfig:
    scoring_raw = raw.get("scoring", {})
    if not isinstance(scoring_raw, dict):
        raise ConfigError("config scoring must be an object")
    scoring = ScoringConfig(
        quality_weight=_number(scoring_raw.get("quality_weight", 0.6), "quality_weight"),
        cost_weight=_number(scoring_raw.get("cost_weight", 0.25), "cost_weight"),
        duration_weight=_number(scoring_raw.get("duration_weight", 0.15), "duration_weight"),
    )
    cfg = SupervisorConfig(
        planner_command=_string(raw.get("planner_command", "codex-task-planner"), "planner_command"),
        harness_command=_string(raw.get("harness_command", "codex-task-harness"), "harness_command"),
        database_path=_string(raw.get("database_path", ".codex-task-supervisor/state/supervisor.sqlite3"), "database_path"),
        reports_root=_string(raw.get("reports_root", ".codex-task-supervisor/reports"), "reports_root"),
        stop_on_first_failure=_bool(raw.get("stop_on_first_failure", False), "stop_on_first_failure"),
        max_parallel_runs=_int(raw.get("max_parallel_runs", 1), "max_parallel_runs"),
        scoring=scoring,
    )
    validate_config(cfg)
    return cfg


def validate_config(config: SupervisorConfig) -> None:
    if config.max_parallel_runs != 1:
        raise ConfigError("max_parallel_runs only supports value 1 in version 1")
    total = config.scoring.quality_weight + config.scoring.cost_weight + config.scoring.duration_weight
    if total <= 0:
        raise ConfigError("scoring weights must sum to a positive value")


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a nonempty string")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be a boolean")
    return value


def _int(value: Any, name: str) -> int:
    if not isinstance(value, int):
        raise ConfigError(f"{name} must be an integer")
    return value


def _number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number")
    return float(value)
