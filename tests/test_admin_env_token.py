import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from admin import admin_token


class AdminTokenTests(unittest.TestCase):
    def test_uses_service_env_file_when_shell_token_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "api.env"
            env_file.write_text("OTHER=value\nACAMP_GAME_ADMIN_TOKEN=staff-token\n", encoding="utf-8")
            with patch.dict(os.environ, {"ACAMP_GAME_ENV_FILE": str(env_file)}, clear=True):
                self.assertEqual("staff-token", admin_token())


if __name__ == "__main__":
    unittest.main()
