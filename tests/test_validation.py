import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_task_supervisor.validation import ValidationError, validate_command


class CommandValidationTests(unittest.TestCase):
    def test_absolute_executable_path_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = Path(tmp) / "tool"
            command.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            command.chmod(0o755)

            validate_command(str(command), "test command")

    def test_relative_executable_path_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                command = Path("tool")
                command.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                command.chmod(0o755)

                validate_command("./tool", "test command")
            finally:
                os.chdir(old)

    def test_path_command_is_accepted_through_shutil_which(self):
        with patch("codex_task_supervisor.validation.shutil.which", return_value="/usr/bin/tool") as which:
            validate_command("tool", "test command")

        which.assert_called_once_with("tool")

    def test_missing_command_fails_clearly(self):
        with patch("codex_task_supervisor.validation.shutil.which", return_value=None):
            with self.assertRaisesRegex(ValidationError, "test command not found on PATH: missing-tool"):
                validate_command("missing-tool", "test command")


if __name__ == "__main__":
    unittest.main()
