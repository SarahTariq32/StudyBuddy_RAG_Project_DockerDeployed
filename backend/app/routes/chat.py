from fastapi import APIRouter, HTTPException, Request
import time
from datetime import datetime, timezone
from app.history.chat_history import get_recent_history, save_message
from app.rag.generator import NOT_ENOUGH, generate_answer_with_meta, non_rag_reply_for_small_talk
from app.rag.pipeline import retrieve_context_with_debug
from app.schemas import AskRequest, AskResponse
from app.database import get_connection

router = APIRouter(tags=["chat"])

INDEXING_MESSAGE = "Your document is still indexing. Please wait a little and try again."
NO_DOCUMENT_MESSAGE = "No PDF is ready yet. Please upload a PDF and wait until it is indexed."


def _looks_like_follow_up(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False
    tokens = [t.strip(".,!?;:\"'()[]{}") for t in q.split()]
    follow_markers = {
        "it", "its", "that", "this", "they", "them", "he", "she", "those", "these",
        "advantages", "benefits", "learn", "improve", "why", "how", "what", "which",
    }
    if any(t in {"it", "its", "that", "this", "they", "them", "he", "she", "those", "these"} for t in tokens):
        return True

    # Explicit standalone follow-up intents that usually need a prior anchor.
    compact = " ".join(tokens)
    follow_phrases = {
        "what are its advantages",
        "what are the advantages",
        "how to learn it",
        "how can i learn it",
        "how can i improve it",
        "why is that",
    }
    return compact in follow_phrases


def _last_user_message(history: list[dict], current_question: str) -> str:
    current_norm = (current_question or "").strip().lower()
    fallback = ""
    for item in reversed(history or []):
        if str(item.get("role") or "") != "user":
            continue
        text = (item.get("message") or "").strip()
        if not text:
            continue
        if text.lower() == current_norm:
            continue
        if not fallback:
            fallback = text
        # Prefer a non-follow-up anchor topic if available.
        if not _looks_like_follow_up(text):
            return text
    return fallback


def _rewrite_with_history(question: str, history: list[dict]) -> str:
    q = (question or "").strip()
    if not q:
        return ""

    previous_user_topic = _last_user_message(history, q)
    if not previous_user_topic:
        return q

    if _looks_like_follow_up(q):
        return f"{q} (about: {previous_user_topic})"
    return q


def _is_unsuccessful_answer(answer: str, retrieved_count: int) -> bool:
    normalized = (answer or "").strip().lower()
    if not normalized:
        return True
    return False


def _answer_outcome(answer: str, retrieved_count: int) -> str:
    normalized = (answer or "").strip().lower()
    if not normalized:
        return "empty"

    no_evidence_answers = {
        NOT_ENOUGH.lower(),
        "i could not find relevant evidence in your uploaded documents for this question.",
    }
    if normalized in no_evidence_answers:
        return "no_evidence"

    if retrieved_count <= 0:
        return "answer_without_context"
    return "answered"


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
    started = time.perf_counter()
    question = (getattr(payload, "question", "") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    total, ready = _documents_state()
    if total == 0:
        return AskResponse(answer=NO_DOCUMENT_MESSAGE)
    if ready == 0:
        return AskResponse(answer=INDEXING_MESSAGE)

    session_id = getattr(payload, "session_id", "default")
    ops = getattr(request.app.state, "ops", None)
    root = None
    if ops is not None:
        root = ops.start_root_trace(question=question, session_id=session_id, path="/ask")

    stage_status = {
        "query_rewrite": "success",
        "retrieval": "success",
        "prompt_creation": "success",
        "llm_generation": "success",
        "final_answer": "success",
    }

    def _finish(answer: str, err: str | None = None, metrics: dict | None = None) -> AskResponse:
        final_metrics = metrics or {
            "overall_ms": round((time.perf_counter() - started) * 1000.0, 2),
            "stage_status": stage_status,
        }
        answer_outcome = _answer_outcome(answer, len(retrieved_docs))
        failed_answer = _is_unsuccessful_answer(answer, len(retrieved_docs))
        status_failed = bool(err) or failed_answer
        stage_status["final_answer"] = "failed" if status_failed else "success"

        trace_id = str(root.trace_id) if root is not None else f"local-{int(time.time() * 1000)}"
        local_trace = {
            "id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "failed" if status_failed else "success",
            "answer_outcome": answer_outcome,
            "question": question,
            "session_id": session_id,
            "query_rewrite": rewritten,
            "multi_queries": rewrites,
            "retrieved_documents": retrieved_docs,
            "retrieved_chunk_count": len(retrieved_docs),
            "prompt_preview": (prompt_text or "")[:1600] if prompt_text else None,
            "llm_response_preview": (answer or "")[:1000],
            "token_usage": token_usage,
            "pipeline_stages": {
                "query_rewrite": {
                    "status": stage_status.get("query_rewrite", "success"),
                    "latency_ms": None,
                    "outputs": {"rewritten_question": rewritten},
                },
                "multi_query_generation": {
                    "status": "success",
                    "latency_ms": None,
                    "outputs": {"queries": rewrites},
                },
                "retrieval": {
                    "status": stage_status.get("retrieval", "success"),
                    "latency_ms": final_metrics.get("retrieval_ms"),
                    "outputs": {
                        "retrieved_documents": retrieved_docs,
                        "retrieved_chunk_count": len(retrieved_docs),
                    },
                },
                "llm_generation": {
                    "status": stage_status.get("llm_generation", "success"),
                    "latency_ms": final_metrics.get("llm_ms"),
                    "outputs": {
                        "answer_preview": (answer or "")[:1000],
                    },
                },
                "final_answer": {
                    "status": stage_status.get("final_answer", "success"),
                    "latency_ms": None,
                    "outputs": {
                        "status": "failed" if status_failed else "success",
                        "outcome": answer_outcome,
                    },
                },
            },
            "durations_ms": {
                "retrieval_ms": final_metrics.get("retrieval_ms"),
                "llm_ms": final_metrics.get("llm_ms"),
                "overall_ms": final_metrics.get("overall_ms"),
            },
            "error": err,
        }
        if ops is not None:
            try:
                ops.record_local_trace(local_trace)
            except Exception:
                pass

        if root is not None:
            ops.end_root(
                root,
                outputs={
                    "answer": answer,
                    "query_rewrite": rewritten,
                    "retrieved_chunk_count": len(retrieved_docs),
                    "prompt_preview": (prompt_text or "")[:1600] if prompt_text else None,
                    "answer_outcome": answer_outcome,
                },
                error=err or ("empty_answer" if failed_answer else None),
                metrics=final_metrics,
            )
        return AskResponse(answer=answer)

    try:
        history_stage = ops.start_stage(root, "query_rewrite", run_type="chain", inputs={"question": question}) if root else None
        history = get_recent_history(session_id)
    except Exception:
        history = []
        stage_status["query_rewrite"] = "failed"
    finally:
        rewritten = _rewrite_with_history(question, history)
        if history_stage:
            ops.end_span(
                history_stage,
                outputs={
                    "rewritten_question": rewritten,
                    "history_messages": len(history),
                },
            )

    prompt_text = None
    token_usage = {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    retrieval_ms = None
    llm_ms = None
    retrieved_docs = []
    rewrites: list[str] = []
    answer = ""

    # LangChain path 
    lc = getattr(request.app.state, "langchain_rag", None)
    if lc and getattr(lc, "enabled", False):
        try:
            retrieval_stage = ops.start_stage(root, "retrieval", run_type="retriever", inputs={"query": rewritten}) if root else None
            llm_details = lc.answer_with_details(rewritten)
            answer = llm_details.get("answer", "")
            # Fallback to small‑talk answer when LangChain returns nothing; if still empty use NOT_ENOUGH
            if not answer:
                answer = non_rag_reply_for_small_talk(question) or NOT_ENOUGH
            prompt_text = llm_details.get("prompt")
            token_usage = llm_details.get("token_usage", token_usage)
            retrieval_ms = (llm_details.get("latency_ms") or {}).get("retrieval_ms")
            llm_ms = (llm_details.get("latency_ms") or {}).get("llm_ms")
            retrieved_docs = llm_details.get("retrieved_documents", []) or []
            rewrites = llm_details.get("rewrites", []) or []

            if retrieval_stage:
                ops.end_span(
                    retrieval_stage,
                    outputs={
                        "retrieved_documents": retrieved_docs,
                        "retrieved_chunk_count": len(retrieved_docs),
                        "retrieval_ms": retrieval_ms,
                    },
                )

            if root and rewrites:
                multi_stage = ops.start_stage(root, "multi_query_generation", run_type="chain", inputs={"question": rewritten})
                ops.end_span(multi_stage, outputs={"queries": rewrites})

            prompt_stage = ops.start_stage(root, "prompt_creation", run_type="prompt", inputs={"query": rewritten}) if root else None
            if prompt_stage:
                ops.end_span(
                    prompt_stage,
                    outputs={
                        "prompt_preview": (prompt_text or "")[:1600],
                    },
                )

            llm_stage = ops.start_stage(root, "llm_generation", run_type="llm", inputs={"provider": "langchain"}) if root else None
            if llm_stage:
                ops.end_span(
                    llm_stage,
                    outputs={
                        "answer_preview": answer[:1000],
                        "token_usage": token_usage,
                        "llm_ms": llm_ms,
                    },
                )

            try:
                save_message(session_id, "user", question)
                save_message(session_id, "assistant", answer)
            except Exception:
                pass
            final_stage = ops.start_stage(root, "final_answer", run_type="chain", inputs={"path": "langchain"}) if root else None
            if final_stage:
                ops.end_span(
                    final_stage,
                    outputs={
                        "status": "failed" if _is_unsuccessful_answer(answer, len(retrieved_docs)) else "success",
                        "outcome": _answer_outcome(answer, len(retrieved_docs)),
                    },
                )
            return _finish(
                answer,
                metrics={
                    "overall_ms": round((time.perf_counter() - started) * 1000.0, 2),
                    "retrieval_ms": retrieval_ms,
                    "llm_ms": llm_ms,
                    "token_usage": token_usage,
                    "retrieved_chunk_count": len(retrieved_docs),
                    "stage_status": stage_status,
                },
            )
        except Exception as exc:
            stage_status["retrieval"] = "failed"
            stage_status["llm_generation"] = "failed"
            if root:
                err_stage = ops.start_stage(root, "llm_generation", run_type="llm", inputs={"provider": "langchain"})
                ops.end_span(err_stage, error=str(exc))
            pass
        finally:
            # Ensure conversation history is stored even on errors
            try:
                if question:
                    save_message(session_id, "user", question)
            except Exception:
                pass
            try:
                if answer:
                    save_message(session_id, "assistant", answer)
            except Exception:
                pass

    # Legacy path
    retrieval_stage = ops.start_stage(root, "retrieval", run_type="retriever", inputs={"query": rewritten}) if root else None
    retrieval_start = time.perf_counter()
    try:
        retrieval_data = retrieve_context_with_debug(rewritten)
        contexts = retrieval_data.get("context", [])
    except Exception as exc:
        stage_status["retrieval"] = "failed"
        if retrieval_stage:
            ops.end_span(retrieval_stage, error=str(exc))
        err_msg = f"Retrieval failed: {exc}"
        if root is not None:
            ops.end_root(root, error=err_msg, metrics={"overall_ms": round((time.perf_counter() - started) * 1000.0, 2), "stage_status": stage_status})
        raise HTTPException(status_code=502, detail=err_msg)
    retrieval_ms = round((time.perf_counter() - retrieval_start) * 1000.0, 2)
    if retrieval_stage:
        ops.end_span(
            retrieval_stage,
            outputs={
                "retrieved_documents": [
                    {
                        "source": c.get("source"),
                        "score": None,
                        "text_preview": (c.get("text") or "")[:240],
                    }
                    for c in contexts
                ],
                "retrieved_chunk_count": len(contexts),
                "retrieval_scores": retrieval_data.get("retrieval_hits", []),
                "retrieval_ms": retrieval_ms,
            },
        )

    rewrites = retrieval_data.get("rewrites", [])
    if root and rewrites:
        multi_stage = ops.start_stage(root, "multi_query_generation", run_type="chain", inputs={"question": rewritten})
        ops.end_span(multi_stage, outputs={"queries": rewrites})

    if not contexts:
        answer = non_rag_reply_for_small_talk(question)
        prompt_text = None
        llm_ms = None
    else:
        try:
            prompt_stage = ops.start_stage(root, "prompt_creation", run_type="prompt", inputs={"question": question}) if root else None
            llm_stage = ops.start_stage(root, "llm_generation", run_type="llm", inputs={"provider": "legacy"}) if root else None

            llm_start = time.perf_counter()
            result = generate_answer_with_meta(question, contexts, history)
            llm_ms = round((time.perf_counter() - llm_start) * 1000.0, 2)
            answer = result.get("answer", "")
            prompt_text = result.get("prompt")
            token_usage = result.get("token_usage", token_usage)

            if prompt_stage:
                ops.end_span(prompt_stage, outputs={"prompt_preview": (prompt_text or "")[:1600]})
            if llm_stage:
                ops.end_span(
                    llm_stage,
                    outputs={
                        "answer_preview": answer[:1000],
                        "token_usage": token_usage,
                        "llm_ms": llm_ms,
                    },
                )
        except TypeError:
            # Backward-compatibility fallback for older function signatures.
            llm_start = time.perf_counter()
            result = generate_answer_with_meta(question, contexts, [])
            llm_ms = round((time.perf_counter() - llm_start) * 1000.0, 2)
            answer = result.get("answer", "")
            prompt_text = result.get("prompt")
            token_usage = result.get("token_usage", token_usage)
        except Exception as exc:
            stage_status["llm_generation"] = "failed"
            if root:
                err_stage = ops.start_stage(root, "llm_generation", run_type="llm", inputs={"provider": "legacy"})
                ops.end_span(err_stage, error=str(exc))
            err_msg = f"LLM generation failed: {exc}"
            if root is not None:
                ops.end_root(root, error=err_msg, metrics={"overall_ms": round((time.perf_counter() - started) * 1000.0, 2), "stage_status": stage_status})
            raise HTTPException(status_code=502, detail=err_msg)

    if answer == NOT_ENOUGH and not contexts:
        answer = non_rag_reply_for_small_talk(question)

    try:
        save_message(session_id, "user", question)
        save_message(session_id, "assistant", answer)
    except Exception:
        pass

    final_stage = ops.start_stage(root, "final_answer", run_type="chain", inputs={"path": "legacy"}) if root else None
    if final_stage:
        ops.end_span(
            final_stage,
            outputs={
                "status": "failed" if _is_unsuccessful_answer(answer, len(contexts)) else "success",
                "outcome": _answer_outcome(answer, len(contexts)),
            },
        )

    return _finish(
        answer,
        metrics={
            "overall_ms": round((time.perf_counter() - started) * 1000.0, 2),
            "retrieval_ms": retrieval_ms,
            "llm_ms": llm_ms,
            "token_usage": token_usage,
            "prompt_preview": (prompt_text or "")[:1600] if prompt_text else None,
            "retrieved_chunk_count": len(contexts),
            "stage_status": stage_status,
        },
    )