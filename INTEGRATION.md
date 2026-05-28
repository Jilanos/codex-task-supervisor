# End-to-End Integration

This guide installs `codex-task-planner`, `codex-task-harness`, and `codex-task-supervisor` into one shared virtual environment so the supervisor can find the planner and harness console scripts on `PATH`.

## Clone the Repositories

```bash
mkdir -p ~/ai-workspaces
cd ~/ai-workspaces

git clone https://github.com/Jilanos/codex-task-planner.git
git clone https://github.com/Jilanos/codex-task-harness.git
git clone https://github.com/Jilanos/codex-task-supervisor.git
```

If the repositories already exist, pull or check out the versions you want to test.

## Create a Shared Virtual Environment

```bash
cd ~/ai-workspaces
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
```

Install all three projects editable into the same active environment:

```bash
python -m pip install -e codex-task-planner
python -m pip install -e codex-task-harness
python -m pip install -e codex-task-supervisor
```

Confirm the console scripts are available:

```bash
which codex-task-planner
which codex-task-harness
which codex-task-supervisor
```

## Smoke Inputs

From the supervisor repository:

```bash
cd ~/ai-workspaces/codex-task-supervisor
```

Use the included request:

```text
examples/requests/smoke_request.md
```

If you need to recreate it:

```bash
mkdir -p examples/requests
cat > examples/requests/smoke_request.md <<'EOF'
Build a tiny Python CLI that accepts a JSON file path, parses it, and prints whether the JSON is valid.

Add minimal tests.
EOF
```

Use the included one-mode matrix:

```text
examples/matrices/smoke.json
```

If you need to recreate it:

```bash
mkdir -p examples/matrices
cat > examples/matrices/smoke.json <<'EOF'
{
  "models": ["gpt-5.3-codex"],
  "reasoning_efforts": ["low"],
  "default_checks": ["python -m compileall src tests", "python -m unittest"],
  "workspace_root": ".codex-task-planner/generated_workspaces",
  "output_root": ".codex-task-planner/generated_artifacts",
  "timeout_seconds": 600
}
EOF
```

The smoke matrix contains one model and one reasoning effort. It writes generated workspaces and harness artifacts under `.codex-task-planner/`.

## Run the Planner Alone

```bash
codex-task-planner create \
  --request-file examples/requests/smoke_request.md \
  --matrix examples/matrices/smoke.json
```

The planner prints a `plan_dir` line. Plans are stored under:

```text
.codex-task-planner/plans/{plan_id}/
```

Each plan directory contains `plan.json`, `tasks.jsonl`, `matrix.json`, `generated_runs.jsonl`, and generated harness task files in `harness_tasks/`.

## Run the Harness on One Generated Task

Pick one task file from the latest generated plan:

```bash
PLAN_DIR="$(ls -td .codex-task-planner/plans/PLAN-* | head -n 1)"
TASK_FILE="$(find "$PLAN_DIR/harness_tasks" -name '*.json' | sort | head -n 1)"
codex-task-harness run --task-file "$TASK_FILE"
```

Harness reports are written under the matrix `output_root`:

```text
.codex-task-planner/generated_artifacts/codex_runs/{task_id}.json
```

The harness also writes stdout and stderr artifacts below the same `output_root`.

## Run the Supervisor End to End

Run from the supervisor repository with the shared virtual environment activated:

```bash
codex-task-supervisor run-benchmark \
  --request-file examples/requests/smoke_request.md \
  --matrix examples/matrices/smoke.json
```

The supervisor uses the default commands `codex-task-planner` and `codex-task-harness`. Because all three repositories are installed into the same active virtual environment, those console scripts resolve through `PATH`.

Supervisor SQLite state is stored at:

```text
.codex-task-supervisor/state/supervisor.sqlite3
```

Supervisor reports are stored at:

```text
.codex-task-supervisor/reports/{plan_id}/summary.json
.codex-task-supervisor/reports/{plan_id}/summary.md
```

## Running with Explicit Commands

Global supervisor options must be placed before the subcommand:

```bash
codex-task-supervisor \
  --planner-command codex-task-planner \
  --harness-command codex-task-harness \
  run-benchmark \
  --request-file examples/requests/smoke_request.md \
  --matrix examples/matrices/smoke.json
```

Absolute and relative executable file paths are also supported:

```bash
codex-task-supervisor \
  --planner-command /absolute/path/to/codex-task-planner \
  --harness-command ./relative/path/to/codex-task-harness \
  run-benchmark \
  --request-file examples/requests/smoke_request.md \
  --matrix examples/matrices/smoke.json
```

## Troubleshooting

### `externally-managed-environment`

If `pip install -e ...` fails with an externally managed environment error, create and activate a virtual environment first:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
```

Then rerun the editable installs inside that environment. Avoid installing these editable development repositories into the system Python.

### `planner command not found on PATH`

Activate the shared virtual environment and confirm the script is installed:

```bash
. ~/ai-workspaces/.venv/bin/activate
which codex-task-planner
python -m pip install -e ~/ai-workspaces/codex-task-planner
```

The same applies to `codex-task-harness`.

### Argparse Global Option Order

`--config`, `--planner-command`, and `--harness-command` are supervisor global options. Put them before the subcommand. This is valid:

```bash
codex-task-supervisor --planner-command codex-task-planner run-benchmark --request-file examples/requests/smoke_request.md --matrix examples/matrices/smoke.json
```

This is invalid because the global option appears after `run-benchmark`:

```bash
codex-task-supervisor run-benchmark --planner-command codex-task-planner --request-file examples/requests/smoke_request.md --matrix examples/matrices/smoke.json
```

### Codex CLI Failures

The planner and supervisor can complete their own validation while the harness still fails if the underlying `codex` executable is missing or returns a nonzero exit code. Check the generated harness report and stdout or stderr artifacts under:

```text
.codex-task-planner/generated_artifacts/
```
