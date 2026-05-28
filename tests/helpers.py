import json
import sys
import tempfile
from pathlib import Path

from codex_task_supervisor.models import ScoringConfig, SupervisorConfig


ROOT = Path(__file__).resolve().parents[1]
FAKE_PLANNER = ROOT / "tests" / "fixtures" / "fake_planner.py"
FAKE_HARNESS = ROOT / "tests" / "fixtures" / "fake_harness.py"


class Workspace:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.request = self.path / "request.md"
        self.matrix = self.path / "matrix.json"
        self.request.write_text("Build a CLI with validation, tests and docs.", encoding="utf-8")
        self.matrix.write_text(
            json.dumps(
                {
                    "models": ["fake-model"],
                    "reasoning_efforts": ["low", "high"],
                    "default_checks": ["python -m unittest"],
                    "workspace_root": str(self.path / "workspaces"),
                    "output_root": str(self.path / "artifacts"),
                    "timeout_seconds": 60,
                }
            ),
            encoding="utf-8",
        )

    def config(self) -> SupervisorConfig:
        return SupervisorConfig(
            planner_command=f"{sys.executable} {FAKE_PLANNER}",
            harness_command=f"{sys.executable} {FAKE_HARNESS}",
            database_path=str(self.path / ".codex-task-supervisor/state/supervisor.sqlite3"),
            reports_root=str(self.path / ".codex-task-supervisor/reports"),
            stop_on_first_failure=False,
            max_parallel_runs=1,
            scoring=ScoringConfig(),
        )

    def cleanup(self):
        self.tmp.cleanup()
