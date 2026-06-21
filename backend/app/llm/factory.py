from app.config import LLM_PROVIDER
from app.llm.gemini_provider import GeminiProvider
from app.llm.groq_provider import GroqProvider

def get_llm_client():
    if LLM_PROVIDER == "gemini":
        return GeminiProvider()
    elif LLM_PROVIDER == "groq":
        return GroqProvider()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")