from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from ip_tray.config import RuntimeConfig, load_runtime_config, save_runtime_config


class RuntimeConfigTests(TestCase):
    def test_load_default_when_file_missing(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            cfg = load_runtime_config(path)
            self.assertEqual(cfg, RuntimeConfig())

    def test_save_and_load_roundtrip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            expected = RuntimeConfig(
                update_interval=2.0,
                public_refresh_interval=60.0,
                request_timeout=5.0,
                notifications_enabled=True,
            )
            save_runtime_config(expected, path)
            actual = load_runtime_config(path)
            self.assertEqual(actual, expected)

    def test_invalid_values_fallback_to_defaults(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                '{"update_interval": 9, "public_refresh_interval": "x", "request_timeout": 0, "notifications_enabled": 1}',
                encoding="utf-8",
            )
            cfg = load_runtime_config(path)
            self.assertEqual(cfg.update_interval, 1.0)
            self.assertEqual(cfg.public_refresh_interval, 30.0)
            self.assertEqual(cfg.request_timeout, 3.5)
            self.assertTrue(cfg.notifications_enabled)
