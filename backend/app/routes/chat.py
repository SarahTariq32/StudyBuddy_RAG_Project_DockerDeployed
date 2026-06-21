from fastapi import APIRouter

from app.history.chat_history import get_recent_history, save_message
from app.rag.generator import generate_answer
from app.rag.pipeline import retrieve_context
from app.schemas import AskRequest, AskResponse

router = APIRouter(tags=["chat"])


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    """
    Full RAG chat flow:
      1. Load recent conversation history for this session
      2. Retrieve relevant parent chunks from Chroma (multi-query)
      3. Build prompt with history + context + question, call LLM
      4. Save the user question and assistant answer to SQLite
    """
    history = get_recent_history(body.session_id)
    context = retrieve_context(body.question)
    answer = generate_answer(body.question, context, history)

    save_message(body.session_id, "user", body.question)
    save_message(body.session_id, "assistant", answer)

    return AskResponse(answer=answer)
