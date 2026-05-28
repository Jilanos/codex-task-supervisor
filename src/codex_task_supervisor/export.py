"""Export helpers for stored benchmark data."""

from __future__ import annotations

import csv
import io
import json

from .database import Database


def export_plan(db: Database, plan_id: str, fmt: str) -> str:
    rows = [dict(row) for row in db.fetch_runs(plan_id)]
    if fmt == "jsonl":
        return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    if fmt == "json":
        return json.dumps(rows, indent=2, sort_keys=True) + "\n"
    if fmt == "csv":
        output = io.StringIO()
        if not rows:
            return ""
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
    raise ValueError(f"unsupported export format: {fmt}")
