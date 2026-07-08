from app.llm.factory import get_llm_client
import re

NOT_ENOUGH = "Context not enough to answer."


def non_rag_reply_for_small_talk(question: str) -> str | None:
    """
    Allow lightweight conversational turns without forcing the user to ask
    a PDF-grounded question first. Everything else remains RAG-gated.
    """
    q = (question or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9\s]", "", q)
    words = normalized.split()

    greetings = {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
    }
    thanks = {"thanks", "thank you", "thx", "ty"}
    byes = {"bye", "goodbye", "see you", "cya"}

    first_word = words[0] if words else ""
    short_text = " ".join(words[:3])

    if normalized in greetings or short_text in greetings or (first_word in {"hi", "hello", "hey"} and len(words) <= 3):
        return "Hi! Ask me anything about your uploaded PDFs."
    if normalized in thanks or short_text in thanks:
        return "You are welcome. Ask me anything about your PDFs whenever you are ready."
    if normalized in byes or short_text in byes:
        return "Bye! I will be here when you want to continue with your PDFs."

    return None


def build_prompt(question: str, context_items: list[dict], history: list[dict]) -> str:
    history_lines = [f"{msg['role']}: {msg['message']}" for msg in history]
    history_text = "\n".join(history_lines) if history_lines else "(none)"

    if context_items:
        context_blocks = []
        for item in context_items:
            source = item.get("source", "")
            text = item.get("text", "")
            label = f"[Source: {source}]\n" if source else ""
            context_blocks.append(f"{label}{text}")
        context_text = "\n\n---\n\n".join(context_blocks)
    else:
        context_text = "(none)"

    return f"""You are a helpful study assistant for PDF-grounded Q&A.

Use ONLY the provided Context. You can synthesize, summarize, and connect ideas across the provided context.
Treat Conversation history as conversational memory, not as factual source.
Do not use outside knowledge, guesses, assumptions, or fabricated facts.
When the context contains source labels like [Source: filename.pdf], cite the relevant source(s) in your answer so the user knows which document the information came from.
If Context is insufficient for the question, respond exactly with the fallback string below.

If the context does not contain enough information to answer the question, reply with exactly this string and nothing else:
{NOT_ENOUGH}

Conversation history:
{history_text}

Context:
{context_text}

Question: {question}"""


def generate_answer(question: str, context_items: list[dict], history: list[dict]) -> str:
    return generate_answer_with_meta(question, context_items, history).get("answer", "")


def generate_answer_with_meta(question: str, context_items: list[dict], history: list[dict]) -> dict:
    prompt = build_prompt(question, context_items, history)
    result = get_llm_client().generate_with_meta(prompt)
    return {
        "answer": result.get("text", ""),
        "prompt": prompt,
        "token_usage": result.get("token_usage", {}),
        "model": result.get("model"),
    }
