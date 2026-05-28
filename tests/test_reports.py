import json
import os
import unittest
from pathlib import Path

from codex_task_supervisor.database import Database
from codex_task_supervisor.reports import generate_reports
from codex_task_supervisor.supervisor import run_benchmark

from .helpers import Workspace


class ReportsTests(unittest.TestCase):
    def test_summary_json_and_markdown_are_generated(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            config = ws.config()
            plan_id = run_benchmark(ws.request, ws.matrix, config)
            json_path, md_path = generate_reports(Database(config.database_path), plan_id, config.reports_root)
            self.assertTrue(Path(json_path).exists())
            self.assertTrue(Path(md_path).exists())
            summary = json.loads(Path(json_path).read_text(encoding="utf-8"))
            self.assertEqual(summary["plan_id"], plan_id)
            self.assertIn("recommendations", summary)
            self.assertIn("# Benchmark Report", Path(md_path).read_text(encoding="utf-8"))
        finally:
            os.chdir(old)
            ws.cleanup()


if __name__ == "__main__":
    unittest.main()
