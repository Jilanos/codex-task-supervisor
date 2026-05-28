import os
import unittest

from codex_task_supervisor.database import Database
from codex_task_supervisor.supervisor import ingest_plan, run_benchmark

from .helpers import Workspace


class SupervisorTests(unittest.TestCase):
    def test_run_benchmark_creates_plan_executes_and_stores_runs(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            config = ws.config()
            plan_id = run_benchmark(ws.request, ws.matrix, config)
            self.assertEqual(plan_id, "PLAN-FAKE-001")
            db = Database(config.database_path)
            self.assertEqual(len(db.fetch_expected_runs(plan_id)), 6)
            runs = db.fetch_runs(plan_id)
            self.assertEqual(len(runs), 6)
            statuses = {row["status"] for row in runs}
            self.assertIn("passed", statuses)
            self.assertIn("blocked", statuses)
            self.assertIn("failed", statuses)
            self.assertGreater(len(db.fetch_all("SELECT * FROM check_results")), 0)
            self.assertGreater(len(db.fetch_all("SELECT * FROM token_usage")), 0)
            self.assertGreater(len(db.fetch_all("SELECT * FROM scores")), 0)
        finally:
            os.chdir(old)
            ws.cleanup()

    def test_planner_output_is_ingested(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            config = ws.config()
            run_benchmark(ws.request, ws.matrix, config)
            plan_id = ingest_plan(".codex-task-planner/plans/PLAN-FAKE-001", config)
            self.assertEqual(plan_id, "PLAN-FAKE-001")
        finally:
            os.chdir(old)
            ws.cleanup()


if __name__ == "__main__":
    unittest.main()
