import os
import unittest

from codex_task_supervisor.database import Database
from codex_task_supervisor.supervisor import run_benchmark, score_existing_plan

from .helpers import Workspace


class DatabaseTests(unittest.TestCase):
    def test_database_schema_initializes(self):
        ws = Workspace()
        try:
            db = Database(ws.config().database_path)
            db.initialize()
            tables = {row["name"] for row in db.fetch_all("SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertIn("plans", tables)
            self.assertIn("runs", tables)
            self.assertIn("scores", tables)
        finally:
            ws.cleanup()

    def test_fetch_reference_corpus_returns_scored_entries_with_features(self):
        ws = Workspace()
        old = os.getcwd()
        os.chdir(ws.path)
        try:
            config = ws.config()
            plan_id = run_benchmark(str(ws.request), str(ws.matrix), config)
            score_existing_plan(plan_id, config)
            db = Database(config.database_path)
            corpus = db.fetch_reference_corpus()
            self.assertGreater(len(corpus), 0)
            entry = corpus[0]
            for key in ("task_id", "plan_id", "features", "model", "reasoning_effort", "final_score"):
                self.assertIn(key, entry)
            self.assertIsInstance(entry["features"], dict)
            self.assertIsNotNone(entry["final_score"])
        finally:
            os.chdir(old)
            ws.cleanup()

    def test_migration_adds_features_json_to_existing_db(self):
        import sqlite3
        ws = Workspace()
        try:
            db = Database(ws.config().database_path)
            db.path.parent.mkdir(parents=True, exist_ok=True)
            # Create schema without features_json to simulate a pre-v0.2 database
            conn = sqlite3.connect(db.path)
            conn.execute("""CREATE TABLE tasks (
                task_id TEXT, plan_id TEXT, title TEXT, task_type TEXT,
                estimated_complexity TEXT, dependencies_json TEXT, prompt TEXT,
                local_context_json TEXT, acceptance_criteria_json TEXT,
                PRIMARY KEY (plan_id, task_id))""")
            conn.commit()
            conn.close()
            # initialize() should add the missing column without raising
            db.initialize()
            conn = sqlite3.connect(db.path)
            cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
            conn.close()
            self.assertIn("features_json", cols)
        finally:
            ws.cleanup()


if __name__ == "__main__":
    unittest.main()
