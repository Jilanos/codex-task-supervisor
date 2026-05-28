# codex-task-supervisor

`codex-task-supervisor` is a standalone local benchmark supervisor for planner and harness based coding experiments.

It orchestrates this pipeline:

```text
high-level request
-> external task planner CLI
-> generated plan files
-> external task harness CLI
-> harness run reports
-> SQLite persistence
-> deterministic scoring
-> final JSON and Markdown benchmark reports
```

The project does not import `codex-task-planner` or `codex-task-harness`. It interacts with them only through CLI commands and generated files.

## What It Does

- Calls an external planner command.
- Detects and ingests a generated plan folder.
- Reads `plan.json`, `tasks.jsonl`, `generated_runs.jsonl`, and harness task files.
- Executes every generated harness task sequentially through an external harness command.
- Reads harness JSON reports from each task's configured `output_root`.
- Stores plans, tasks, modes, expected runs, run reports, checks, token usage, changed files, artifacts, and scores in SQLite.
- Computes deterministic quality, cost, duration, efficiency, and final scores.
- Generates final `summary.json` and `summary.md` reports.

## What It Does Not Do

- It does not call Codex directly.
- It does not call any LLM.
- It does not make network calls.
- It does not implement parallel execution in v0.1.
- It does not import planner or harness Python modules.
- It does not estimate real monetary cost from token prices.

## Relationship With codex-task-planner

The supervisor expects a planner CLI compatible with:

```bash
codex-task-planner create --request-file {request_file} --matrix {matrix_file}
```

The default planner command is `codex-task-planner`, but it can be replaced:

```bash
codex-task-supervisor --planner-command "python tests/fixtures/fake_planner.py" run-benchmark --request-file request.md --matrix matrix.json
```

The planner must produce a plan directory containing:

- `plan.json`
- `tasks.jsonl`
- `generated_runs.jsonl`
- generated harness task files

## Relationship With codex-task-harness

The supervisor expects a harness CLI compatible with:

```bash
codex-task-harness run --task-file {task_file}
```

The default harness command is `codex-task-harness`, but it can be replaced:

```bash
codex-task-supervisor --harness-command "python tests/fixtures/fake_harness.py" execute-plan --plan-id PLAN-FAKE-001
```

For each task file, the supervisor expects the harness report at:

```text
{output_root}/codex_runs/{task_id}.json
```

## Installation

```bash
pip install -e .
```

The project uses a `src/` layout and only the Python standard library.

## CLI Usage

Run the complete benchmark pipeline:

```bash
codex-task-supervisor run-benchmark --request-file examples/requests/simple_request.md --matrix examples/matrices/default.json
```

Ingest an existing plan:

```bash
codex-task-supervisor ingest-plan --plan-dir .codex-task-planner/plans/PLAN-xxx
```

Execute all expected runs for an ingested plan:

```bash
codex-task-supervisor execute-plan --plan-id PLAN_ID
```

Score a plan:

```bash
codex-task-supervisor score-plan --plan-id PLAN_ID
```

Generate reports:

```bash
codex-task-supervisor report --plan-id PLAN_ID
```

Inspect stored data:

```bash
codex-task-supervisor list-plans
codex-task-supervisor list-runs --plan-id PLAN_ID
codex-task-supervisor show-run RUN_ID
```

Export run data:

```bash
codex-task-supervisor export --plan-id PLAN_ID --format jsonl
```

Supported export formats are `jsonl`, `json`, and `csv`.

## Configuration

Default local state:

```text
.codex-task-supervisor/state/supervisor.sqlite3
```

Default reports folder:

```text
.codex-task-supervisor/reports/
```

Example config:

```json
{
  "planner_command": "codex-task-planner",
  "harness_command": "codex-task-harness",
  "database_path": ".codex-task-supervisor/state/supervisor.sqlite3",
  "reports_root": ".codex-task-supervisor/reports",
  "stop_on_first_failure": false,
  "max_parallel_runs": 1,
  "scoring": {
    "quality_weight": 0.6,
    "cost_weight": 0.25,
    "duration_weight": 0.15
  }
}
```

Use it with:

```bash
codex-task-supervisor --config examples/config/supervisor.json list-plans
```

`max_parallel_runs` is present for future compatibility, but v0.1 only supports `1`. Any other value fails clearly.

## Database Schema Overview

SQLite tables:

- `plans`: plan metadata and status
- `tasks`: planned subtasks
- `modes`: model and reasoning effort combinations
- `expected_runs`: generated task and mode combinations expected to run
- `runs`: harness execution results
- `check_results`: command check results per run
- `token_usage`: input, output, reasoning, and total tokens
- `changed_files`: changed files reported by the harness
- `scores`: deterministic score outputs
- `artifacts`: run artifacts

No ORM is used.

## Scoring Method

Quality starts from run status:

- `passed`: 100
- `blocked`: 50
- `failed`: 0

Adjustments:

- subtract 5 if no checks were reported
- subtract 5 if changed files are empty for an implementation task
- subtract 10 if `codex_exit_code` is nonzero
- clamp between 0 and 100

Cost score uses `total_tokens` when available. For a plan, the lowest-token run gets 100, the highest-token run gets 0, and intermediate runs are linearly scaled. If token usage is missing, cost score is `null`.

Duration score uses `duration_seconds`. The fastest run gets 100, the slowest gets 0, and intermediate runs are linearly scaled.

Efficiency score uses weighted averages:

```text
quality: 0.6
cost: 0.25
duration: 0.15
```

If cost is missing, efficiency is computed from quality and duration only. If quality is below 70, efficiency is capped at 50.

Final score is the same as efficiency score for v0.1.

## Report Outputs

Reports are written to:

```text
.codex-task-supervisor/reports/{plan_id}/summary.json
.codex-task-supervisor/reports/{plan_id}/summary.md
```

The JSON summary includes:

- plan ID and request
- task, mode, expected run, and completed run counts
- passed, blocked, and failed counts
- best run per task
- best modes overall
- total tokens
- total duration
- average final score
- all runs
- deterministic recommendations

The Markdown report includes a readable benchmark summary, best runs, best modes, failed or blocked runs, cost and duration summary, and recommendations.

## Testing With Fake Tools

Tests do not use real `codex-task-planner`, real `codex-task-harness`, Codex, LLMs, or network calls.

Fake tools live in:

```text
tests/fixtures/fake_planner.py
tests/fixtures/fake_harness.py
```

The fake planner writes a valid plan folder. The fake harness writes valid harness reports and deterministically simulates passed, blocked, and failed runs.

Run tests:

```bash
python -m unittest
```

## Exit Codes

- `0`: success
- `1`: validation error
- `2`: planner failure
- `3`: harness failure
- `4`: database error
- `5`: report generation error

## Limitations

Version 0.1 executes runs sequentially. It assumes the planner and harness CLIs honor their file contracts. It scores only deterministic report fields and does not inspect code diffs, estimate real cost, retry failures, or select execution modes dynamically.

## Future Roadmap

- v0.2: parallel execution
- v0.3: retry and escalation policy
- v0.4: richer scoring with diff analysis
- v0.5: cost estimation using real token prices
- v0.6: optimized execution mode using the cheapest sufficient model
- v0.7: intelligent router trained from historical runs
- v0.8: integration into a larger Orchestia-style orchestration system
