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

    def test_recommend_returns_json_with_required_keys(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            import json as _json
            config = ws.config()
            common = ["--planner-command", config.planner_command, "--harness-command", config.harness_command]
            # Run benchmark so the corpus has scored entries
            main(common + ["run-benchmark", "--request-file", str(ws.request), "--matrix", str(ws.matrix)])
            main(common + ["score-plan", "--plan-id", "PLAN-FAKE-001"])
            features = _json.dumps({
                "task_type": "implementation",
                "domains": ["cli", "validation"],
                "complexity_estimate": "low",
            })
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(common + ["recommend", "--features", features])
            self.assertEqual(code, 0)
            result = _json.loads(buf.getvalue())
            for key in ("recommended_model", "reasoning_effort", "confidence", "based_on", "top_matches"):
                self.assertIn(key, result)
        finally:
            os.chdir(old)
            ws.cleanup()

    def test_recommend_fails_without_corpus(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            import json as _json
            config = ws.config()
            common = ["--planner-command", config.planner_command, "--harness-command", config.harness_command]
            features = _json.dumps({"task_type": "implementation", "domains": []})
            code = main(common + ["recommend", "--features", features])
            self.assertEqual(code, 1)
        finally:
            os.chdir(old)
            ws.cleanup()


if __name__ == "__main__":
    unittest.main()
