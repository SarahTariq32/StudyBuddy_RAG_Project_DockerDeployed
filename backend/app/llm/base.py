from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send a prompt to the LLM, return its text response."""
        pass

    def generate_with_meta(self, prompt: str) -> dict:
        """Best-effort metadata wrapper; providers can override for token usage."""
        return {
            "text": self.generate(prompt),
            "token_usage": {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            },
            "model": None,
        }