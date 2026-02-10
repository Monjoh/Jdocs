import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from settings import (
    derive_db_path,
    get_config_dir,
    is_configured,
    load_settings,
    save_settings,
)


class TestGetConfigDir(unittest.TestCase):

    @patch("settings.platform.system", return_value="Windows")
    def test_windows_path(self, _mock):
        path = get_config_dir()
        self.assertTrue(str(path).endswith(os.path.join("AppData", "Local", "jdocs")))

    @patch("settings.platform.system", return_value="Darwin")
    def test_macos_path(self, _mock):
        path = get_config_dir()
        self.assertTrue(str(path).endswith(os.path.join(".config", "jdocs")))

    @patch("settings.platform.system", return_value="Linux")
    def test_linux_path(self, _mock):
        path = get_config_dir()
        self.assertTrue(str(path).endswith(os.path.join(".config", "jdocs")))


class TestLoadSaveSettings(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_dir = Path(self.tmpdir) / "jdocs"
        self.patcher = patch("settings.get_config_dir", return_value=self.config_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_returns_defaults_when_no_file(self):
        settings = load_settings()
        self.assertEqual(settings["root_folder"], "")
        self.assertEqual(settings["db_path"], "")

    def test_save_and_load_roundtrip(self):
        save_settings({"root_folder": "/tmp/myroot", "db_path": "/tmp/myroot/.jdocs/jdocs.db"})
        settings = load_settings()
        self.assertEqual(settings["root_folder"], "/tmp/myroot")
        self.assertEqual(settings["db_path"], "/tmp/myroot/.jdocs/jdocs.db")

    def test_save_creates_directories(self):
        self.assertFalse(self.config_dir.exists())
        save_settings({"root_folder": "/some/path"})
        self.assertTrue(self.config_dir.exists())
        self.assertTrue((self.config_dir / "config.json").exists())

    def test_load_handles_corrupt_json(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_dir / "config.json", "w") as f:
            f.write("{broken json!!!}")
        settings = load_settings()
        self.assertEqual(settings["root_folder"], "")

    def test_load_merges_with_defaults(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_dir / "config.json", "w") as f:
            json.dump({"root_folder": "/foo"}, f)
        settings = load_settings()
        self.assertEqual(settings["root_folder"], "/foo")
        self.assertIn("db_path", settings)


class TestDeriveDbPath(unittest.TestCase):

    def test_derives_path(self):
        result = derive_db_path("/home/user/docs")
        expected = str(Path("/home/user/docs") / ".jdocs" / "jdocs.db")
        self.assertEqual(result, expected)

    def test_windows_style_path(self):
        result = derive_db_path("C:\\Users\\me\\docs")
        self.assertIn(".jdocs", result)
        self.assertTrue(result.endswith("jdocs.db"))


class TestIsConfigured(unittest.TestCase):

    def test_empty_root_is_not_configured(self):
        self.assertFalse(is_configured({"root_folder": ""}))

    def test_nonexistent_dir_is_not_configured(self):
        self.assertFalse(is_configured({"root_folder": "/nonexistent/path/xyz123"}))

    def test_existing_dir_is_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(is_configured({"root_folder": tmpdir}))


if __name__ == "__main__":
    unittest.main()
