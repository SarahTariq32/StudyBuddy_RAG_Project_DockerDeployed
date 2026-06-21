from app.llm.factory import get_llm_client

NOT_ENOUGH = "Context not enough to answer."


def build_prompt(question: str, context_parents: list[str], history: list[dict]) -> str:
    history_lines = [f"{msg['role']}: {msg['message']}" for msg in history]
    history_text = "\n".join(history_lines) if history_lines else "(none)"

    context_text = "\n\n---\n\n".join(context_parents) if context_parents else "(none)"

    return f"""You are a helpful assistant. Answer the question using ONLY the context provided below. Do not use outside knowledge.

If the context does not contain enough information to answer the question, reply with exactly this string and nothing else:
{NOT_ENOUGH}

Conversation history:
{history_text}

Context:
{context_text}

Question: {question}"""


def generate_answer(question: str, context_parents: list[str], history: list[dict]) -> str:
    prompt = build_prompt(question, context_parents, history)
    return get_llm_client().generate(prompt)
