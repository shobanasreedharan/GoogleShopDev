"""Shared GPT-5.6 primary-model client with a caller-provided fallback."""

import os
from collections.abc import Callable


GPT56_MODEL = "gpt-5.6"


def generate_gpt56_text(prompt: str) -> str:
    """Return non-empty GPT-5.6 output or raise so the caller can fall back."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    response = OpenAI(api_key=api_key).responses.create(
        model=GPT56_MODEL,
        input=prompt,
    )
    text = getattr(response, "output_text", "")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("GPT-5.6 returned an empty or invalid response")
    return text.strip()


def generate_primary_or_fallback(
    prompt: str,
    fallback: Callable[[str], str],
    *,
    log_prefix: str,
    primary: Callable[[str], str] | None = None,
) -> tuple[str, str]:
    """Use the primary generator first, then the supplied fallback if it cannot respond."""
    try:
        text = (primary or generate_gpt56_text)(prompt)
        model_used = "primary" if primary else GPT56_MODEL
    except Exception as error:
        failed_label = "primary generator" if primary else "GPT-5.6"
        print(f"[{log_prefix}] {failed_label} failed; falling back to Gemini: {error}")
        text = fallback(prompt)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Gemini returned an empty or invalid response")
        text = text.strip()
        model_used = "gemini"

    print(f"[{log_prefix}] response served by: {model_used}")
    return text, model_used
