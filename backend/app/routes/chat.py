from fastapi import APIRouter, HTTPException

from app.history.chat_history import get_recent_history, save_message
from app.rag.generator import NOT_ENOUGH, generate_answer, non_rag_reply_for_small_talk
from app.rag.pipeline import retrieve_context
from app.schemas import AskRequest, AskResponse

router = APIRouter(tags=["chat"])


# @router.post("/ask", response_model=AskResponse)
# def ask(body: AskRequest):
#     """
#     Full RAG chat flow:
#       1. Load recent conversation history for this session
#       2. Retrieve relevant parent chunks from Chroma (multi-query)
#       3. Build prompt with history + context + question, call LLM
#       4. Save the user question and assistant answer to SQLite
#     """
#     history = get_recent_history(body.session_id)
#     context = retrieve_context(body.question)

#     if not context:
#         answer = NOT_ENOUGH
#     else:
#         try:
#             answer = generate_answer(body.question, context, history)
#         except (RuntimeError, ValueError) as exc:
#             raise HTTPException(status_code=502, detail=str(exc)) from exc

#     save_message(body.session_id, "user", body.question)
#     save_message(body.session_id, "assistant", answer)

#     return AskResponse(answer=answer)


# ...existing code...
# @router.post("/ask", response_model=AskResponse)
# def ask(body: AskRequest):
#     """
#     Full RAG chat flow:
#       1. Load recent conversation history for this session
#       2. Retrieve relevant parent chunks from Chroma (multi-query)
#       3. Build prompt with history + context + question, call LLM
#       4. Save the user question and assistant answer to SQLite
#     """
#     history = get_recent_history(body.session_id)
#     context = retrieve_context(body.question)

#     if not context:
#         answer = NOT_ENOUGH
#     else:
#         try:
#             answer = generate_answer(body.question, context, history)
#         except Exception as exc:
#             raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc

#     save_message(body.session_id, "user", body.question)
#     save_message(body.session_id, "assistant", answer)

#     return AskResponse(answer=answer)
# ...existing code...


# ...existing code...
@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    session_id = body.session_id.strip()
    question = body.question.strip()

    if not session_id:
        raise HTTPException(status_code=422, detail="session_id is required")
    if not question:
        raise HTTPException(status_code=422, detail="question is required")

    # Save user message first, so history is preserved even if downstream fails.
    save_message(session_id, "user", question)

    # Handle lightweight chat immediately without invoking retrieval or LLM.
    small_talk_answer = non_rag_reply_for_small_talk(question)
    if small_talk_answer is not None:
        save_message(session_id, "assistant", small_talk_answer)
        return AskResponse(answer=small_talk_answer)

    history = get_recent_history(session_id)
    context = retrieve_context(question)

    if not context:
        answer = NOT_ENOUGH
    else:
        try:
            answer = generate_answer(question, context, history)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc

    save_message(session_id, "assistant", answer)
    return AskResponse(answer=answer)
# ...existing code...