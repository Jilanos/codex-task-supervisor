#!/usr/bin/env python3
"""Fake codex-task-planner used by tests."""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--request-file", required=True)
    create.add_argument("--matrix", required=True)
    args = parser.parse_args()

    request = Path(args.request_file).read_text(encoding="utf-8").strip()
    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    plan_id = "PLAN-FAKE-001"
    plan_dir = Path(".codex-task-planner/plans") / plan_id
    harness_dir = plan_dir / "harness_tasks"
    harness_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    tasks = [
        task("TASK-001", "Implement feature", "implementation", []),
        task("TASK-002", "Add tests", "test", ["TASK-001"]),
        task("TASK-003", "Final verification", "verification", ["TASK-002"]),
    ]
    modes = [
        {
            "mode_id": f"{model}_{effort}",
            "model": model,
            "reasoning_effort": effort,
            "timeout_seconds": matrix.get("timeout_seconds", 60),
        }
        for model, effort in itertools.product(matrix["models"], matrix["reasoning_efforts"])
    ]
    runs = []
    for item, mode in itertools.product(tasks, modes):
        run_id = f"{item['task_id']}__{mode['mode_id']}"
        task_file = harness_dir / f"{run_id}.json"
        payload = {
            "task_id": run_id,
            "prompt": f"Global context:\n{request}\n\nTask:\n{item['prompt']}",
            "model": mode["model"],
            "reasoning_effort": mode["reasoning_effort"],
            "workspace": str(Path(matrix["workspace_root"]) / run_id),
            "checks": matrix.get("default_checks", []),
            "output_root": matrix["output_root"],
            "timeout_seconds": mode["timeout_seconds"],
        }
        task_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        runs.append(
            {
                "run_id": run_id,
                "task_id": item["task_id"],
                "mode_id": mode["mode_id"],
                "model": mode["model"],
                "reasoning_effort": mode["reasoning_effort"],
                "workspace": payload["workspace"],
                "checks": payload["checks"],
                "output_root": payload["output_root"],
                "timeout_seconds": payload["timeout_seconds"],
                "task_file": str(task_file),
            }
        )
    plan = {
        "plan_id": plan_id,
        "created_at": created_at,
        "request": request,
        "global_context": {"project_goal": request, "constraints": [], "assumptions": []},
        "tasks": tasks,
        "modes": modes,
        "generated_runs": runs,
    }
    (plan_dir / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (plan_dir / "tasks.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in tasks), encoding="utf-8")
    (plan_dir / "generated_runs.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in runs), encoding="utf-8")
    print(f"created {plan_id}")
    print(f"plan_dir {plan_dir}")
    return 0


def task(task_id: str, title: str, task_type: str, dependencies: list[str]) -> dict[str, object]:
    return {
        "task_id": task_id,
        "title": title,
        "task_type": task_type,
        "estimated_complexity": "low",
        "dependencies": dependencies,
        "prompt": title,
        "local_context": {"scope": title},
        "acceptance_criteria": [f"{title} is complete."],
        "checks": ["python -m unittest"],
        "features": {
            "task_type": task_type,
            "domains": ["cli", "validation"] if task_type == "implementation" else ["tests"],
            "has_cli": task_type == "implementation",
            "has_validation": task_type == "implementation",
            "has_tests": task_type == "test",
            "has_io": task_type == "implementation",
            "has_state": False,
            "complexity_estimate": "low",
            "domain_count": 2 if task_type == "implementation" else 1,
            "dependency_count": len(dependencies),
            "acceptance_criteria_count": 1,
            "check_count": 1,
            "prompt_word_count": len(title.split()),
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
