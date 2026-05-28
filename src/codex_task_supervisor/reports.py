"""JSON and Markdown report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .database import Database
from .scoring import average


def generate_reports(db: Database, plan_id: str, reports_root: str | Path) -> tuple[Path, Path]:
    summary = build_summary(db, plan_id)
    directory = Path(reports_root) / plan_id
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "summary.json"
    md_path = directory / "summary.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    return json_path, md_path


def build_summary(db: Database, plan_id: str) -> dict[str, Any]:
    plan = db.fetch_plan(plan_id)
    if plan is None:
        raise ValueError(f"plan not found: {plan_id}")
    rows = db.fetch_all(
        """SELECT r.*, s.quality_score, s.cost_score, s.duration_score, s.efficiency_score, s.final_score,
                  tu.total_tokens
           FROM runs r
           LEFT JOIN scores s ON s.run_id = r.run_id
           LEFT JOIN token_usage tu ON tu.run_id = r.run_id
           WHERE r.plan_id = ?
           ORDER BY r.run_id""",
        (plan_id,),
    )
    run_dicts = [dict(row) for row in rows]
    best_by_task = _best_by(run_dicts, "task_id")
    best_modes = _best_modes(run_dicts)
    total_tokens = sum(row["total_tokens"] or 0 for row in rows)
    total_duration = sum(row["duration_seconds"] or 0 for row in rows)
    final_scores = [row["final_score"] for row in rows if row["final_score"] is not None]
    return {
        "plan_id": plan_id,
        "request": plan["request"],
        "task_count": plan["task_count"],
        "mode_count": plan["mode_count"],
        "expected_run_count": plan["generated_run_count"],
        "completed_run_count": len(rows),
        "passed_count": sum(1 for row in rows if row["status"] == "passed"),
        "blocked_count": sum(1 for row in rows if row["status"] == "blocked"),
        "failed_count": sum(1 for row in rows if row["status"] == "failed"),
        "best_runs_by_task": best_by_task,
        "best_modes_overall": best_modes,
        "total_tokens": total_tokens,
        "total_duration_seconds": total_duration,
        "average_final_score": average(final_scores),
        "runs": run_dicts,
        "recommendations": recommendations(run_dicts, best_modes),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    failed = [run for run in summary["runs"] if run["status"] in {"failed", "blocked"}]
    lines = [
        f"# Benchmark Report: {summary['plan_id']}",
        "",
        "## Request",
        "",
        summary["request"],
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Tasks | {summary['task_count']} |",
        f"| Modes | {summary['mode_count']} |",
        f"| Expected runs | {summary['expected_run_count']} |",
        f"| Completed runs | {summary['completed_run_count']} |",
        f"| Passed | {summary['passed_count']} |",
        f"| Blocked | {summary['blocked_count']} |",
        f"| Failed | {summary['failed_count']} |",
        f"| Average final score | {_fmt(summary['average_final_score'])} |",
        "",
        "## Best Run Per Task",
        "",
    ]
    for task_id, run in summary["best_runs_by_task"].items():
        lines.append(f"- {task_id}: {run['run_id']} score {_fmt(run.get('final_score'))}")
    lines.extend(["", "## Best Model/Reasoning Combinations", ""])
    for mode in summary["best_modes_overall"]:
        lines.append(f"- {mode['mode_id']}: average score {_fmt(mode['average_final_score'])}, average tokens {_fmt(mode['average_tokens'])}")
    lines.extend(["", "## Failed Or Blocked Runs", ""])
    if failed:
        for run in failed:
            lines.append(f"- {run['run_id']}: {run['status']}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Cost And Duration Summary",
            "",
            f"- Total tokens: {summary['total_tokens']}",
            f"- Total duration seconds: {_fmt(summary['total_duration_seconds'])}",
            "",
            "## Recommendations",
            "",
        ]
    )
    for item in summary["recommendations"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def recommendations(runs: list[dict[str, Any]], best_modes: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    if any(run.get("total_tokens") is None for run in runs):
        notes.append("Cost analysis is incomplete because token usage is missing for one or more runs.")
    if best_modes:
        best = best_modes[0]
        if (best.get("average_final_score") or 0) >= 70:
            notes.append(f"Mode {best['mode_id']} is the strongest efficient candidate based on average score.")
    high = [run for run in runs if run.get("reasoning_effort") == "high"]
    non_high = [run for run in runs if run.get("reasoning_effort") != "high"]
    if high and non_high and _avg_score(high) <= _avg_score(non_high):
        notes.append("High reasoning effort is not improving score in this benchmark.")
    low = [run for run in runs if run.get("reasoning_effort") == "low"]
    if low and sum(1 for run in low if run.get("status") == "failed") >= max(1, len(low) // 2):
        notes.append("Low reasoning effort often fails for this plan.")
    if not notes:
        notes.append("No strong deterministic recommendation is available from this run set.")
    return notes


def _best_by(runs: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for run in runs:
        current = result.get(run[key])
        if current is None or (run.get("final_score") or -1) > (current.get("final_score") or -1):
            result[run[key]] = run
    return result


def _best_modes(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        grouped.setdefault(run["mode_id"], []).append(run)
    rows = []
    for mode_id, items in grouped.items():
        rows.append(
            {
                "mode_id": mode_id,
                "average_final_score": _avg_score(items),
                "average_tokens": average([item["total_tokens"] for item in items if item.get("total_tokens") is not None]),
            }
        )
    return sorted(rows, key=lambda row: (row["average_final_score"] or 0, -(row["average_tokens"] or 0)), reverse=True)


def _avg_score(runs: list[dict[str, Any]]) -> float:
    return average([run["final_score"] for run in runs if run.get("final_score") is not None]) or 0.0


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
