"""HTTP tests for the mode-aware judging route.

These tests need FastAPI and httpx (TestClient). The plain AI test run
uses the system Python without those packages, so the class is skipped
there and runs in the service virtualenv.
"""

from __future__ import annotations

import base64
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    from app.main import app
except Exception:  # pragma: no cover - depends on the test environment
    TestClient = None
    app = None


@unittest.skipIf(TestClient is None, "fastapi/httpx not installed")
class APIModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def _post(self, mode: str):
        payload = {
            "audio": base64.b64encode(b"fake audio bytes").decode("ascii"),
            "model": "quick",
            "surah": 94,
            "ayah_from": 1,
            "ayah_to": 1,
            "mode": mode,
        }
        with patch(
            "app.asr.from_audio_to_text",
            return_value="أَلِمْ نَشْرَحْ لَكَ صَدْرَكَ",
        ):
            return self.client.post("/api/transcribe/json", json=payload)

    def test_standard_mode_marks_vowel_error(self):
        response = self._post("standard")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["words"][0]["status"], "mispronounced")
        self.assertLess(data["score"], 1.0)

    def test_remove_tashkeel_mode_ignores_vowel_error(self):
        response = self._post("remove_tashkeel")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["words"][0]["status"], "ok")
        self.assertEqual(data["score"], 1.0)

    def test_warsh_mode_is_accepted(self):
        response = self._post("warsh")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["words"][0]["status"], "mispronounced")

    def test_unknown_mode_is_400(self):
        response = self._post("bogus")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
