from google import genai
from google.genai import errors as genai_errors

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing. Add it to your .env file.")
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def generate(self, prompt: str) -> str:
        return self.generate_with_meta(prompt).get("text", "")

    def generate_with_meta(self, prompt: str) -> dict:
        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
        except genai_errors.ClientError as exc:
            raise RuntimeError(
                f"Gemini request failed for model '{GEMINI_MODEL}'. "
                f"Check GEMINI_MODEL in .env. Details: {exc}"
            ) from exc

        text = response.text
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        usage = getattr(response, "usage_metadata", None)
        return {
            "text": text,
            "token_usage": {
                "input_tokens": getattr(usage, "prompt_token_count", None),
                "output_tokens": getattr(usage, "candidates_token_count", None),
                "total_tokens": getattr(usage, "total_token_count", None),
            },
            "model": GEMINI_MODEL,
        }
