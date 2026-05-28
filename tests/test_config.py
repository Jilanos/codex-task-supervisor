import json
import unittest
from pathlib import Path

from codex_task_supervisor.config import ConfigError, load_config, parse_config


class ConfigTests(unittest.TestCase):
    def test_configuration_loads_correctly(self):
        config = load_config(Path("examples/config/supervisor.json"))
        self.assertEqual(config.planner_command, "codex-task-planner")
        self.assertEqual(config.max_parallel_runs, 1)
        self.assertEqual(config.scoring.quality_weight, 0.6)

    def test_parallel_value_fails_clearly(self):
        with self.assertRaisesRegex(ConfigError, "max_parallel_runs"):
            parse_config({"max_parallel_runs": 2})


if __name__ == "__main__":
    unittest.main()
