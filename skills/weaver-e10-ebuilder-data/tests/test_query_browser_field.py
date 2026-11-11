from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from query_browser_field import (
    KIND_ROUTES,
    build_form_param,
    normalize_matches,
    resolve_kind,
    route_from_field,
)


class BrowserFieldRoutingTests(unittest.TestCase):
    def test_builtin_people_and_organization_routes(self) -> None:
        expected = {
            "人员": ("hrm", "resource", "人员"),
            "部门": ("hrm", "department", "部门"),
            "分部": ("hrm", "subcompany", "分部"),
        }
        for label, route in expected.items():
            with self.subTest(label=label):
                self.assertEqual(KIND_ROUTES[resolve_kind(label)], route)

    def test_uses_actual_browser_configuration(self) -> None:
        field = {
            "config": {
                "browserType": {
                    "module": "task",
                    "type": "taskTypeBrowser",
                }
            }
        }
        self.assertEqual(
            route_from_field(field),
            ("task", "taskTypeBrowser", "field.browserType"),
        )

    def test_preserves_field_context_in_form_param(self) -> None:
        field = {
            "id": "field-1",
            "browserParams": {
                "formId": "form-1",
                "layoutId": "layout-1",
                "fieldId": "field-1",
                "serviceModule": "ebuilderform",
            },
        }
        value = build_form_param(field)
        self.assertIsNotNone(value)
        payload = json.loads(value or "{}")
        self.assertEqual(payload["formId"], "form-1")
        self.assertEqual(payload["layoutId"], "layout-1")
        self.assertEqual(payload["fieldId"], "field-1")

    def test_normalizes_browser_results_for_form_writes(self) -> None:
        payload = {
            "data": {
                "total": 1,
                "data": [
                    {
                        "id": "1001",
                        "name": "秦珂珂",
                        "departmentName": "研发部",
                    }
                ],
            }
        }
        matches, total = normalize_matches(payload, 20)
        self.assertEqual(total, 1)
        self.assertEqual(
            matches[0]["dataOption"],
            {"optionId": "1001", "content": "秦珂珂"},
        )
        self.assertEqual(matches[0]["details"]["departmentName"], "研发部")


if __name__ == "__main__":
    unittest.main()
