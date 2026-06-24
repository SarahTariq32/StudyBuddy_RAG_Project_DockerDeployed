from fastapi import APIRouter, HTTPException

from app.history.chat_history import get_recent_history, save_message
from app.llm.factory import get_llm_client
from app.rag.generator import NOT_ENOUGH, generate_answer, non_rag_reply_for_small_talk
from app.rag.pipeline import retrieve_context
from app.schemas import AskRequest, AskResponse
from app.database import get_connection

router = APIRouter(tags=["chat"])

INDEXING_MESSAGE = "Your document is still indexing. Please wait a little and try again."
NO_DOCUMENT_MESSAGE = "No PDF is ready yet. Please upload a PDF and wait until it is indexed."


def _rewrite_with_history(question: str, history: list[dict]) -> str:
    """
    Rewrite a potentially ambiguous follow-up question into a standalone
    search query using recent conversation context.
    Falls back to the original question on any failure.
    """
    if not history:
        return question

    history_lines = [
        f"{msg.get('role', '')}: {msg.get('message', '').strip()}"
        for msg in history[-6:]
        if msg.get("message")
    ]
    if not history_lines:
        return question

    prompt = (
        "Rewrite the user's latest question into a standalone search query for document retrieval. "
        "Keep names/titles explicit when the latest question uses pronouns. "
        "Return only one short rewritten query and nothing else.\n\n"
        "Conversation:\n" + "\n".join(history_lines) + "\n"
        f"Latest question: {question}"
    )

    try:
        rewritten = get_llm_client().generate(prompt).strip()
    except Exception:
        return question

    return rewritten or question


def _documents_state() -> tuple[int, int]:
    conn = get_connection()
    try:
        ready = conn.execute("SELECT COUNT(*) FROM documents WHERE status = 'ready'").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        return ready, total
    finally:
        conn.close()


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    session_id = body.session_id.strip()
    question = body.question.strip()

    if not session_id:
        raise HTTPException(status_code=422, detail="session_id is required")
    if not question:
        raise HTTPException(status_code=422, detail="question is required")

    # Persist the user turn immediately so history is never lost.
    save_message(session_id, "user", question)

    # Short-circuit small-talk without touching retrieval or the LLM.
    small_talk_answer = non_rag_reply_for_small_talk(question)
    if small_talk_answer is not None:
        save_message(session_id, "assistant", small_talk_answer)
        return AskResponse(answer=small_talk_answer)

    ready_count, total_docs = _documents_state()
    if ready_count == 0:
        answer = INDEXING_MESSAGE if total_docs > 0 else NO_DOCUMENT_MESSAGE
        save_message(session_id, "assistant", answer)
        return AskResponse(answer=answer)

    history = get_recent_history(session_id)

    # Resolve pronouns / ambiguous references before retrieval so that
    # follow-up questions ("tell me more", "what about his job?") embed
    # into the correct region of the vector space.
    retrieval_query = _rewrite_with_history(question, history) if history else question

    try:
        context = retrieve_context(retrieval_query)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Retrieval error: {exc}") from exc

    if not context:
        answer = NOT_ENOUGH
    else:
        try:
            answer = generate_answer(question, context, history)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc

    save_message(session_id, "assistant", answer)
    return AskResponse(answer=answer)