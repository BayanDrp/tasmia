"""Backend priority logic: no torch, no network, both paths patched.

Run from ai/:  PYTHONPATH="../core" python3 -m unittest discover tests -q

The Space path is pure stdlib. The local path imports torch lazily, and
these tests replace it with a mock, so the system python needs no heavy
packages.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from app import asr


class BackendPriorityTest(unittest.TestCase):
    def test_space_success_never_calls_local(self):
        with mock.patch.object(asr, "_space_transcription", return_value="نص سحابي") as space, \
             mock.patch.object(asr, "_local_transcription") as local, \
             mock.patch.object(asr, "SPACE_ASR_ENABLED", True), \
             mock.patch.object(asr, "SPACE_ASR_PREFER", True):
            result = asr.from_audio_to_text("clip.wav", "quick")

        self.assertEqual(result, "نص سحابي")
        space.assert_called_once_with("clip.wav", "quick", "ar")
        local.assert_not_called()

    def test_space_failure_uses_local(self):
        with mock.patch.object(asr, "_space_transcription", side_effect=OSError("space down")), \
             mock.patch.object(asr, "_local_transcription", return_value="نص محلي") as local, \
             mock.patch.object(asr, "SPACE_ASR_ENABLED", True), \
             mock.patch.object(asr, "SPACE_ASR_PREFER", True):
            result = asr.from_audio_to_text("clip.wav", "quick")

        self.assertEqual(result, "نص محلي")
        local.assert_called_once_with("clip.wav", "quick", "ar")

    def test_both_fail_local_error_wins(self):
        local_error = RuntimeError("local boom")
        with mock.patch.object(asr, "_space_transcription", side_effect=OSError("space down")), \
             mock.patch.object(asr, "_local_transcription", side_effect=local_error), \
             mock.patch.object(asr, "SPACE_ASR_ENABLED", True), \
             mock.patch.object(asr, "SPACE_ASR_PREFER", True):
            with self.assertRaises(RuntimeError) as caught:
                asr.from_audio_to_text("clip.wav", "quick")

        self.assertIs(caught.exception, local_error)
        self.assertEqual(str(caught.exception.__cause__), "space down")

    def test_local_only_when_space_disabled(self):
        with mock.patch.object(asr, "_space_transcription") as space, \
             mock.patch.object(asr, "_local_transcription", return_value="نص محلي") as local, \
             mock.patch.object(asr, "SPACE_ASR_ENABLED", False), \
             mock.patch.object(asr, "SPACE_ASR_PREFER", True):
            result = asr.from_audio_to_text("clip.wav", "quick")

        self.assertEqual(result, "نص محلي")
        local.assert_called_once_with("clip.wav", "quick", "ar")
        space.assert_not_called()

    def test_local_failure_raises_when_space_disabled(self):
        local_error = RuntimeError("no torch")
        with mock.patch.object(asr, "_space_transcription") as space, \
             mock.patch.object(asr, "_local_transcription", side_effect=local_error), \
             mock.patch.object(asr, "SPACE_ASR_ENABLED", False), \
             mock.patch.object(asr, "SPACE_ASR_PREFER", True):
            with self.assertRaises(RuntimeError) as caught:
                asr.from_audio_to_text("clip.wav", "quick")

        self.assertIs(caught.exception, local_error)
        space.assert_not_called()

    def test_local_first_uses_space_on_failure(self):
        with mock.patch.object(asr, "_local_transcription", side_effect=RuntimeError("no torch")), \
             mock.patch.object(asr, "_space_transcription", return_value="نص بديل") as space, \
             mock.patch.object(asr, "SPACE_ASR_ENABLED", True), \
             mock.patch.object(asr, "SPACE_ASR_PREFER", False):
            result = asr.from_audio_to_text("clip.wav", "quick")

        self.assertEqual(result, "نص بديل")
        space.assert_called_once_with("clip.wav", "quick", "ar")

    def test_local_first_success_never_calls_space(self):
        with mock.patch.object(asr, "_local_transcription", return_value="نص محلي") as local, \
             mock.patch.object(asr, "_space_transcription") as space, \
             mock.patch.object(asr, "SPACE_ASR_ENABLED", True), \
             mock.patch.object(asr, "SPACE_ASR_PREFER", False):
            result = asr.from_audio_to_text("clip.wav", "quick")

        self.assertEqual(result, "نص محلي")
        local.assert_called_once_with("clip.wav", "quick", "ar")
        space.assert_not_called()


class SpaceRequestShapeTest(unittest.TestCase):
    def test_space_call_posts_base64_with_metadata(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return '{"transcription": "ا او او او كلام"}'.encode("utf-8")

        def fake_urllib(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        handle, path = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(handle, "wb") as temp_file:
            temp_file.write(b"fake audio bytes")

        try:
            with mock.patch.object(asr.urllib.request, "urlopen", side_effect=fake_urllib):
                result = asr._space_transcription(path, "quick", "ar")
        finally:
            os.unlink(path)

        self.assertTrue(captured["url"].endswith("/api/transcribe/json"))
        self.assertEqual(captured["timeout"], asr.SPACE_ASR_TIMEOUT)
        self.assertTrue(captured["body"]["filename"].endswith(".wav"))
        self.assertIn("audio_base64", captured["body"])
        self.assertIn("كلام", result)


if __name__ == "__main__":
    unittest.main()
