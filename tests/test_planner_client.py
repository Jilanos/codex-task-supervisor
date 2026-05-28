import os
import unittest

from codex_task_supervisor.planner_client import run_planner

from .helpers import Workspace


class PlannerClientTests(unittest.TestCase):
    def test_planner_client_calls_fake_planner(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            result = run_planner(ws.config().planner_command, ws.request, ws.matrix)
            self.assertEqual(result.command_result.exit_code, 0)
            self.assertEqual(result.plan_dir, ".codex-task-planner/plans/PLAN-FAKE-001")
        finally:
            os.chdir(old)
            ws.cleanup()


if __name__ == "__main__":
    unittest.main()
