import os
import unittest

from codex_task_supervisor.database import Database
from codex_task_supervisor.scoring import score_plan
from codex_task_supervisor.supervisor import run_benchmark

from .helpers import Workspace


class ScoringTests(unittest.TestCase):
    def test_scores_are_computed_and_missing_token_usage_does_not_fail(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            config = ws.config()
            plan_id = run_benchmark(ws.request, ws.matrix, config)
            scores = score_plan(Database(config.database_path), plan_id, config.scoring)
            self.assertEqual(len(scores), 6)
            self.assertTrue(any(score["cost_score"] is None for score in scores))
            self.assertTrue(all(score["final_score"] >= 0 for score in scores))
        finally:
            os.chdir(old)
            ws.cleanup()


if __name__ == "__main__":
    unittest.main()
