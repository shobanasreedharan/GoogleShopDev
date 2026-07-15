from backend.engines.gemini_engine import generate_with_gemini
from backend.engines.fallback_engine import generate_fallback


def safe_ai_generate(prompt: str):
    try:
        result = generate_with_gemini(prompt)

        if result is None or result == "":
            raise ValueError("Empty Gemini response")

        return result

    except Exception as e:
        print("[AI Router] Gemini failed → fallback used:", e)
        return generate_fallback(prompt)