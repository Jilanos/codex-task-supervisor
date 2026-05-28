import io
import os
import unittest
from contextlib import redirect_stdout

from codex_task_supervisor.cli import main

from .helpers import Workspace


class CliTests(unittest.TestCase):
    def test_cli_commands_work(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            config = ws.config()
            common = ["--planner-command", config.planner_command, "--harness-command", config.harness_command]
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(common + ["run-benchmark", "--request-file", str(ws.request), "--matrix", str(ws.matrix)])
            self.assertEqual(code, 0)
            self.assertIn("completed PLAN-FAKE-001", out.getvalue())

            for command in [
                ["list-plans"],
                ["list-runs", "--plan-id", "PLAN-FAKE-001"],
                ["show-run", "TASK-001__fake-model_low"],
                ["export", "--plan-id", "PLAN-FAKE-001", "--format", "jsonl"],
                ["report", "--plan-id", "PLAN-FAKE-001"],
            ]:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    self.assertEqual(main(common + command), 0)
                self.assertTrue(buf.getvalue())
        finally:
            os.chdir(old)
            ws.cleanup()


if __name__ == "__main__":
    unittest.main()
