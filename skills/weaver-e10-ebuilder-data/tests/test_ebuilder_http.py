from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ebuilder_http import resolve_api_prefix, resolve_origin


class EBuilderHttpTests(unittest.TestCase):
    def test_resolves_origin_and_supported_api_prefixes(self) -> None:
        self.assertEqual(
            resolve_origin("https://e10.example.invalid/"),
            "https://e10.example.invalid",
        )
        self.assertEqual(resolve_api_prefix("/api/ebuilder"), "/api/ebuilder")
        self.assertEqual(
            resolve_api_prefix("/api/ebuilder1247863311668019213"),
            "/api/ebuilder1247863311668019213",
        )

    def test_rejects_user_information_and_business_paths(self) -> None:
        for value in (
            "https://u:p@e10.example.invalid",
            "https://e10.example.invalid/api/ebuilder",
        ):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                resolve_origin(value)


if __name__ == "__main__":
    unittest.main()
