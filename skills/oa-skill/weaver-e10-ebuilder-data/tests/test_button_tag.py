from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from button_tag import normalize_tags, queryButtonsByTags

ORIGIN = "https://e10.example.invalid"
MOCK_COOKIE = {"EBUILDER_COOKIE": "ETEAMSID=test-session"}


class NormalizeTagsTests(unittest.TestCase):
    def test_splits_strips_and_dedupes_keeping_order(self) -> None:
        self.assertEqual(
            normalize_tags("approve, reject, approve,  "),
            "approve,reject",
        )

    def test_accepts_list_input(self) -> None:
        self.assertEqual(normalize_tags(["a", " b", "a", "c"]), "a,b,c")

    def test_empty_or_blank_raises(self) -> None:
        for value in ("", " , , "):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                normalize_tags(value)

    def test_rejects_non_string_or_list(self) -> None:
        with self.assertRaises(RuntimeError):
            normalize_tags(123)  # type: ignore[arg-type]


class QueryButtonsByTagsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = patch.dict(os.environ, MOCK_COOKIE)
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()

    def test_builds_normalized_payload_and_passthroughs(self) -> None:
        response = {"success": True, "data": []}
        with patch("button_tag.request_json", return_value=response) as mocked:
            result = queryButtonsByTags(
                200001, 300001, "approve, reject", "0", origin=ORIGIN
            )
        mocked.assert_called_once()
        _, path, body, _ = mocked.call_args.args
        self.assertTrue(path.endswith("/api/ebuilder/form/button/queryByTags"))
        payload = json.loads(body)
        self.assertEqual(payload["objId"], 200001)
        self.assertEqual(payload["dataId"], 300001)
        self.assertEqual(payload["tags"], "approve,reject")
        self.assertEqual(payload["viewType"], "0")
        self.assertIs(result, response)

    def test_accepts_int_view_type_and_list_tags(self) -> None:
        with patch("button_tag.request_json", return_value={}) as mocked:
            queryButtonsByTags(200001, 300001, ["approve", "reject"], 2, origin=ORIGIN)
        payload = json.loads(mocked.call_args.args[2])
        self.assertEqual(payload["tags"], "approve,reject")
        self.assertEqual(payload["viewType"], "2")

    def test_rejects_unsupported_view_type_before_request(self) -> None:
        with patch("button_tag.request_json", side_effect=AssertionError("不应发请求")) as mocked:
            with self.assertRaises(RuntimeError):
                queryButtonsByTags(200001, 300001, "approve", "1", origin=ORIGIN)
        mocked.assert_not_called()

    def test_rejects_empty_tags_before_request(self) -> None:
        with patch("button_tag.request_json", side_effect=AssertionError("不应发请求")) as mocked:
            with self.assertRaises(RuntimeError):
                queryButtonsByTags(200001, 300001, " , ", "0", origin=ORIGIN)
        mocked.assert_not_called()

    def test_single_button_success_false_is_preserved(self) -> None:
        response = {
            "success": True,
            "data": [
                {
                    "buttonId": "100001",
                    "buttonName": "同意",
                    "tag": "approve",
                    "success": False,
                    "errorMessage": "该按钮无权限显示",
                    "actions": [],
                }
            ],
        }
        with patch("button_tag.request_json", return_value=response):
            result = queryButtonsByTags(200001, 300001, "approve", "0", origin=ORIGIN)
        button = result["data"][0]
        self.assertFalse(button["success"])
        self.assertEqual(button["errorMessage"], "该按钮无权限显示")


if __name__ == "__main__":
    unittest.main()
