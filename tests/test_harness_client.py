import json
import unittest
from pathlib import Path

from codex_task_supervisor.harness_client import run_harness

from .helpers import Workspace


class HarnessClientTests(unittest.TestCase):
    def test_harness_client_calls_fake_harness_and_parses_report(self):
        ws = Workspace()
        try:
            task_file = ws.path / "task.json"
            task_file.write_text(
                json.dumps(
                    {
                        "task_id": "TASK-001__fake-model_low",
                        "model": "fake-model",
                        "reasoning_effort": "low",
                        "workspace": str(ws.path / "workspace"),
                        "checks": ["python -m unittest"],
                        "output_root": str(ws.path / "artifacts"),
                        "timeout_seconds": 60,
                        "prompt": "Global context:\nTask",
                    }
                ),
                encoding="utf-8",
            )
            result = run_harness(ws.config().harness_command, task_file)
            self.assertEqual(result.report["status"], "passed")
            self.assertTrue(Path(result.report_path).exists())
        finally:
            ws.cleanup()


if __name__ == "__main__":
    unittest.main()
