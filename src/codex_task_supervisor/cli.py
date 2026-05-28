"""Command line interface for codex-task-supervisor."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from .config import ConfigError, load_config
from .database import Database
from .export import export_plan
from .supervisor import HarnessFailure, PlannerFailure, ReportFailure, execute_plan, generate_existing_report, ingest_plan, run_benchmark, score_existing_plan
from .validation import ValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-task-supervisor")
    parser.add_argument("--config", default=None)
    parser.add_argument("--planner-command", default=None)
    parser.add_argument("--harness-command", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run-benchmark")
    run.add_argument("--request-file", required=True)
    run.add_argument("--matrix", required=True)

    ingest = sub.add_parser("ingest-plan")
    ingest.add_argument("--plan-dir", required=True)

    execute = sub.add_parser("execute-plan")
    execute.add_argument("--plan-id", required=True)

    score = sub.add_parser("score-plan")
    score.add_argument("--plan-id", required=True)

    report = sub.add_parser("report")
    report.add_argument("--plan-id", required=True)

    sub.add_parser("list-plans")

    list_runs = sub.add_parser("list-runs")
    list_runs.add_argument("--plan-id", required=True)

    show_run = sub.add_parser("show-run")
    show_run.add_argument("run_id")

    export = sub.add_parser("export")
    export.add_argument("--plan-id", required=True)
    export.add_argument("--format", choices=["jsonl", "json", "csv"], default="jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.planner_command:
            config = type(config)(**{**config.__dict__, "planner_command": args.planner_command})
        if args.harness_command:
            config = type(config)(**{**config.__dict__, "harness_command": args.harness_command})
        db = Database(config.database_path)
        db.initialize()

        if args.command == "run-benchmark":
            plan_id = run_benchmark(args.request_file, args.matrix, config)
            print(f"completed {plan_id}")
            return 0
        if args.command == "ingest-plan":
            plan_id = ingest_plan(args.plan_dir, config)
            print(f"ingested {plan_id}")
            return 0
        if args.command == "execute-plan":
            execute_plan(args.plan_id, config)
            print(f"executed {args.plan_id}")
            return 0
        if args.command == "score-plan":
            score_existing_plan(args.plan_id, config)
            print(f"scored {args.plan_id}")
            return 0
        if args.command == "report":
            json_path, md_path = generate_existing_report(args.plan_id, config)
            print(f"summary_json {json_path}")
            print(f"summary_md {md_path}")
            return 0
        if args.command == "list-plans":
            for row in db.fetch_all("SELECT * FROM plans ORDER BY created_at"):
                print(f"{row['plan_id']} {row['status']} tasks={row['task_count']} runs={row['generated_run_count']}")
            return 0
        if args.command == "list-runs":
            for row in db.fetch_runs(args.plan_id):
                print(f"{row['run_id']} {row['status']} {row['model']} {row['reasoning_effort']}")
            return 0
        if args.command == "show-run":
            row = db.fetch_run(args.run_id)
            if row is None:
                print(f"error: run not found: {args.run_id}", file=sys.stderr)
                return 1
            print(json.dumps(dict(row), indent=2, sort_keys=True))
            return 0
        if args.command == "export":
            print(export_plan(db, args.plan_id, args.format), end="")
            return 0
    except (ConfigError, ValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except PlannerFailure as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except HarnessFailure as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except sqlite3.Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except ReportFailure as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    parser.error("unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
