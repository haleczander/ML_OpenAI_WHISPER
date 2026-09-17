from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.app_config import AppConfig


class AppConfigTests(unittest.TestCase):
    def test_first_load_creates_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state" / "config.json"

            config = AppConfig.load(path, environ={})

            self.assertEqual(config, AppConfig(host="0.0.0.0", port=8000, https=False))
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"host": "0.0.0.0", "port": 8000, "https": False},
            )

    def test_environment_overrides_persistent_config_without_rewriting_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            original = {"host": "127.0.0.1", "port": 9000, "https": False}
            path.write_text(json.dumps(original), encoding="utf-8")

            config = AppConfig.load(
                path,
                environ={"APP_HOST": "0.0.0.0", "APP_PORT": "8443", "APP_SSL": "true"},
            )

            self.assertEqual(config, AppConfig(host="0.0.0.0", port=8443, https=True))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)

    def test_invalid_values_are_rejected(self) -> None:
        invalid_payloads = [
            {"port": 0},
            {"port": 65536},
            {"port": "not-a-port"},
            {"host": ""},
            {"https": "sometimes"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        AppConfig.load(path, environ={})

    def test_windows_powershell_utf8_bom_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(
                json.dumps({"host": "0.0.0.0", "port": 8000, "https": True}),
                encoding="utf-8-sig",
            )

            config = AppConfig.load(path, environ={})

            self.assertTrue(config.https)

    def test_browser_urls_include_localhost_and_lan_addresses(self) -> None:
        config = AppConfig(host="0.0.0.0", port=8123, https=True)
        with patch("src.app_config.discover_lan_addresses", return_value=["192.168.1.20"]):
            self.assertEqual(
                config.browser_urls(),
                ["https://localhost:8123", "https://192.168.1.20:8123"],
            )


if __name__ == "__main__":
    unittest.main()
