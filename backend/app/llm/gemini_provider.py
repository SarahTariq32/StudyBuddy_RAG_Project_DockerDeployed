from google import genai
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.llm.base import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text