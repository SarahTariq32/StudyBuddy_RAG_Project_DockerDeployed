from fastapi import APIRouter, HTTPException, Request
from app.history.chat_history import get_recent_history, save_message
from app.rag.generator import NOT_ENOUGH, generate_answer, non_rag_reply_for_small_talk
from app.rag.pipeline import retrieve_context
from app.schemas import AskRequest, AskResponse
from app.database import get_connection

router = APIRouter(tags=["chat"])

INDEXING_MESSAGE = "Your document is still indexing. Please wait a little and try again."
NO_DOCUMENT_MESSAGE = "No PDF is ready yet. Please upload a PDF and wait until it is indexed."


def _rewrite_with_history(question: str, history: list[dict]) -> str:
    if not history:
        return question
    return question


def _documents_state() -> tuple[int, int]:
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        ready = conn.execute("SELECT COUNT(*) FROM documents WHERE status='ready'").fetchone()[0]
        return int(total), int(ready)
    finally:
        conn.close()


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, request: Request):
    question = (getattr(payload, "question", "") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    total, ready = _documents_state()
    if total == 0:
        return AskResponse(answer=NO_DOCUMENT_MESSAGE)
    if ready == 0:
        return AskResponse(answer=INDEXING_MESSAGE)

    session_id = getattr(payload, "session_id", "default")

    try:
        history = get_recent_history(session_id)
    except Exception:
        history = []

    rewritten = _rewrite_with_history(question, history)

    # LangChain path (optional)
    lc = getattr(request.app.state, "langchain_rag", None)
    if lc and getattr(lc, "enabled", False):
        try:
            answer = lc.answer(rewritten)
            try:
                save_message(session_id, "user", question)
                save_message(session_id, "assistant", answer)
            except Exception:
                pass
            return AskResponse(answer=answer)
        except Exception:
            pass

    # Legacy path
    contexts = retrieve_context(rewritten)
    if not contexts:
        answer = non_rag_reply_for_small_talk(question)
    else:
        try:
            answer = generate_answer(question, contexts, history)
        except TypeError:
            answer = generate_answer(question, contexts)

    if answer == NOT_ENOUGH and not contexts:
        answer = non_rag_reply_for_small_talk(question)

    try:
        save_message(session_id, "user", question)
        save_message(session_id, "assistant", answer)
    except Exception:
        pass

    return AskResponse(answer=answer)