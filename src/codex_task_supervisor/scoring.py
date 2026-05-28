"""Deterministic scoring for benchmark runs."""

from __future__ import annotations

import statistics
from typing import Any

from .database import Database
from .models import ScoringConfig


def score_plan(db: Database, plan_id: str, config: ScoringConfig) -> list[dict[str, Any]]:
    rows = db.fetch_all(
        """SELECT r.*, t.task_type, tu.total_tokens,
                  (SELECT COUNT(*) FROM check_results c WHERE c.run_id = r.run_id) AS check_count,
                  (SELECT COUNT(*) FROM changed_files f WHERE f.run_id = r.run_id) AS changed_file_count
           FROM runs r
           JOIN tasks t ON t.plan_id = r.plan_id AND t.task_id = r.task_id
           LEFT JOIN token_usage tu ON tu.run_id = r.run_id
           WHERE r.plan_id = ?
           ORDER BY r.run_id""",
        (plan_id,),
    )
    token_values = [row["total_tokens"] for row in rows if row["total_tokens"] is not None]
    duration_values = [row["duration_seconds"] for row in rows if row["duration_seconds"] is not None]
    scores = []
    for row in rows:
        quality, notes = quality_score(row)
        cost = normalized_inverse(row["total_tokens"], token_values) if row["total_tokens"] is not None else None
        duration = normalized_inverse(row["duration_seconds"], duration_values) if row["duration_seconds"] is not None else 0.0
        efficiency = efficiency_score(quality, cost, duration, config)
        if quality < 70:
            efficiency = min(efficiency, 50.0)
            notes.append("efficiency capped because quality is below 70")
        score = {
            "run_id": row["run_id"],
            "quality_score": quality,
            "cost_score": cost,
            "duration_score": duration,
            "efficiency_score": efficiency,
            "final_score": efficiency,
            "scoring_notes": notes,
        }
        db.insert_score(row["run_id"], score)
        scores.append(score)
    return scores


def quality_score(row: Any) -> tuple[float, list[str]]:
    notes: list[str] = []
    status = row["status"]
    if status == "passed":
        score = 100.0
    elif status == "blocked":
        score = 50.0
    else:
        score = 0.0
    if row["check_count"] == 0:
        score -= 5
        notes.append("no checks were reported")
    if row["task_type"] == "implementation" and row["changed_file_count"] == 0:
        score -= 5
        notes.append("implementation task reported no changed files")
    if row["codex_exit_code"] not in (None, 0):
        score -= 10
        notes.append("codex exit code was nonzero")
    return max(0.0, min(100.0, score)), notes


def normalized_inverse(value: float | int | None, values: list[float | int]) -> float:
    if value is None or not values:
        return 0.0
    low = min(values)
    high = max(values)
    if high == low:
        return 100.0
    return max(0.0, min(100.0, 100.0 * (high - float(value)) / (high - low)))


def efficiency_score(quality: float, cost: float | None, duration: float, config: ScoringConfig) -> float:
    if cost is None:
        total = config.quality_weight + config.duration_weight
        return (quality * config.quality_weight + duration * config.duration_weight) / total
    total = config.quality_weight + config.cost_weight + config.duration_weight
    return (quality * config.quality_weight + cost * config.cost_weight + duration * config.duration_weight) / total


def average(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None
