import unittest

from codex_task_supervisor.database import Database

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


if __name__ == "__main__":
    unittest.main()
