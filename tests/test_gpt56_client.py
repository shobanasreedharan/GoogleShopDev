import sys
import types
import unittest
from unittest.mock import patch

from backend.core import gpt56_client


class GPT56ClientTests(unittest.TestCase):
    def test_primary_response_is_returned_with_gpt56_model_name(self):
        with patch.object(gpt56_client, "generate_gpt56_text", return_value="Primary answer"):
            text, model_used = gpt56_client.generate_primary_or_fallback(
                "prompt", lambda _: "Gemini answer", log_prefix="test"
            )

        self.assertEqual(text, "Primary answer")
        self.assertEqual(model_used, "gpt-5.6")

    def test_failure_or_invalid_primary_response_uses_gemini_fallback(self):
        with patch.object(gpt56_client, "generate_gpt56_text", side_effect=ValueError("empty")):
            text, model_used = gpt56_client.generate_primary_or_fallback(
                "prompt", lambda _: "Gemini answer", log_prefix="test"
            )

        self.assertEqual(text, "Gemini answer")
        self.assertEqual(model_used, "gemini")

    def test_custom_primary_generator_is_supported(self):
        text, model_used = gpt56_client.generate_primary_or_fallback(
            "prompt",
            lambda _: "Fallback answer",
            log_prefix="test",
            primary=lambda _: "Custom primary answer",
        )

        self.assertEqual(text, "Custom primary answer")
        self.assertEqual(model_used, "primary")

    def test_openai_response_text_is_validated(self):
        fake_openai = types.ModuleType("openai")

        class FakeOpenAI:
            def __init__(self, api_key):
                self.responses = types.SimpleNamespace(
                    create=lambda **_: types.SimpleNamespace(output_text="  GPT answer  ")
                )

        fake_openai.OpenAI = FakeOpenAI
        with patch.dict(sys.modules, {"openai": fake_openai}), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False
        ):
            self.assertEqual(gpt56_client.generate_gpt56_text("prompt"), "GPT answer")


if __name__ == "__main__":
    unittest.main()
