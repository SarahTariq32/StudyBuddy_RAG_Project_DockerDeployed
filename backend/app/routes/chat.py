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

STAGE_NAMES = ("query_rewrite", "embedding", "retrieval", "llm_generation", "final_answer")


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


def _new_stage_state() -> dict:
    return {
        name: {
            "execution_status": "Skipped",
            "status": "skipped",
            "outcome": None,
            "failure_reason": None,
            "latency_ms": None,
        }
        for name in STAGE_NAMES
    }


def _set_stage_completed(stages: dict, name: str, *, latency_ms=None, outcome: str | None = None) -> None:
    stage = stages.setdefault(name, {})
    stage["execution_status"] = "Completed"
    stage["status"] = "success"
    stage["failure_reason"] = None
    stage["latency_ms"] = latency_ms
    stage["outcome"] = outcome


def _set_stage_failed(stages: dict, name: str, reason: str, *, latency_ms=None, outcome: str | None = None) -> None:
    stage = stages.setdefault(name, {})
    stage["execution_status"] = "Failed"
    stage["status"] = "failed"
    stage["failure_reason"] = str(reason)
    stage["latency_ms"] = latency_ms
    stage["outcome"] = outcome


def _set_stage_skipped(stages: dict, name: str, *, outcome: str | None = None) -> None:
    stage = stages.setdefault(name, {})
    stage["execution_status"] = "Skipped"
    stage["status"] = "skipped"
    stage["failure_reason"] = None
    stage["latency_ms"] = None
    stage["outcome"] = outcome


def _first_failed_reason(stages: dict) -> str | None:
    for name in STAGE_NAMES:
        st = stages.get(name, {}) or {}
        if st.get("execution_status") == "Failed":
            reason = st.get("failure_reason")
            return f"{name}: {reason}" if reason else name
    return None


def _overall_request_failed(stages: dict, *, fallback_recovered: bool) -> bool:
    any_critical_failed = any((stages.get(name, {}) or {}).get("execution_status") == "Failed" for name in STAGE_NAMES)
    return any_critical_failed and not fallback_recovered


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

    stage_status = _new_stage_state()
    fallback_mode = None
    fallback_reason = None

    def _finish(answer: str, err: str | None = None, metrics: dict | None = None) -> AskResponse:
        retrieved_count = len(retrieved_docs)
        answer_outcome = _answer_outcome(answer, retrieved_count)
        llm_only = retrieved_count <= 0

        if answer_outcome == "no_evidence":
            _set_stage_completed(stage_status, "final_answer", outcome="no_relevant_context")
        elif answer_outcome == "empty":
            _set_stage_failed(stage_status, "final_answer", "empty answer")
        else:
            _set_stage_completed(stage_status, "final_answer", outcome=answer_outcome)

        recovered_from_failure = bool(fallback_mode == "fallback_after_pipeline_error" and (answer or "").strip())
        stage_failed = _overall_request_failed(stage_status, fallback_recovered=recovered_from_failure)
        failed_answer = _is_unsuccessful_answer(answer, retrieved_count)
        status_failed = bool(err) or failed_answer or stage_failed

        request_failure_reason = err or _first_failed_reason(stage_status)
        response_source = "llm_only_response" if llm_only else "rag_context"
        if fallback_mode == "fallback_after_pipeline_error":
            response_source = "fallback_after_pipeline_error"

        final_metrics = metrics or {
            "overall_ms": round((time.perf_counter() - started) * 1000.0, 2),
            "retrieved_chunk_count": retrieved_count,
        }
        final_metrics["stage_status"] = stage_status
        final_metrics["answer_outcome"] = answer_outcome
        final_metrics["response_source"] = response_source
        final_metrics["request_failure_reason"] = request_failure_reason
        final_metrics["fallback_mode"] = fallback_mode
        final_metrics["overall_status"] = "failed" if status_failed else "success"
        final_metrics["fallback_reason"] = fallback_reason

        trace_id = str(root.trace_id) if root is not None else f"local-{int(time.time() * 1000)}"
        local_trace = {
            "id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "failed" if status_failed else "success",
            "answer_outcome": answer_outcome,
            "response_source": response_source,
            "request_failure_reason": request_failure_reason,
            "fallback_mode": fallback_mode,
            "fallback_reason": fallback_reason,
            "question": question,
            "session_id": session_id,
            "query_rewrite": rewritten,
            "multi_queries": rewrites,
            "retrieved_documents": retrieved_docs,
            "retrieved_chunk_count": retrieved_count,
            "prompt_preview": (prompt_text or "")[:1600] if prompt_text else None,
            "llm_response_preview": (answer or "")[:1000],
            "token_usage": token_usage,
            "pipeline_stages": {
                "query_rewrite": {
                    **(stage_status.get("query_rewrite") or {}),
                    "outputs": {"rewritten_question": rewritten},
                },
                "embedding": {
                    **(stage_status.get("embedding") or {}),
                    "outputs": {},
                },
                "multi_query_generation": {
                    "execution_status": "Completed" if rewrites else "Skipped",
                    "status": "success" if rewrites else "skipped",
                    "latency_ms": None,
                    "outcome": "expanded_queries" if rewrites else None,
                    "failure_reason": None,
                    "outputs": {"queries": rewrites},
                },
                "retrieval": {
                    **(stage_status.get("retrieval") or {}),
                    "latency_ms": final_metrics.get("retrieval_ms"),
                    "outputs": {
                        "retrieved_documents": retrieved_docs,
                        "retrieved_chunk_count": retrieved_count,
                        "retrieval_outcome": (stage_status.get("retrieval") or {}).get("outcome"),
                    },
                },
                "llm_generation": {
                    **(stage_status.get("llm_generation") or {}),
                    "latency_ms": final_metrics.get("llm_ms"),
                    "outputs": {
                        "answer_preview": (answer or "")[:1000],
                    },
                },
                "final_answer": {
                    **(stage_status.get("final_answer") or {}),
                    "outputs": {
                        "status": "failed" if status_failed else "success",
                        "outcome": answer_outcome,
                        "source": response_source,
                    },
                },
            },
            "durations_ms": {
                "retrieval_ms": final_metrics.get("retrieval_ms"),
                "llm_ms": final_metrics.get("llm_ms"),
                "overall_ms": final_metrics.get("overall_ms"),
            },
            "error": request_failure_reason if status_failed else None,
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
                    "retrieved_chunk_count": retrieved_count,
                    "prompt_preview": (prompt_text or "")[:1600] if prompt_text else None,
                    "answer_outcome": answer_outcome,
                    "response_source": response_source,
                    "request_failure_reason": request_failure_reason,
                    "fallback_mode": fallback_mode,
                    "fallback_reason": fallback_reason,
                    "overall_status": "failed" if status_failed else "success",
                },
                error=request_failure_reason if status_failed else None,
                metrics=final_metrics,
            )
        return AskResponse(answer=answer)

    rewrite_started = time.perf_counter()
    try:
        history_stage = ops.start_stage(root, "query_rewrite", run_type="chain", inputs={"question": question}) if root else None
        history = get_recent_history(session_id)
    except Exception:
        history = []
        _set_stage_failed(stage_status, "query_rewrite", "history lookup failed")
    finally:
        rewritten = _rewrite_with_history(question, history)
        if (stage_status.get("query_rewrite") or {}).get("execution_status") != "Failed":
            _set_stage_completed(
                stage_status,
                "query_rewrite",
                latency_ms=round((time.perf_counter() - rewrite_started) * 1000.0, 2),
                outcome="rewritten" if rewritten != question else "as_is",
            )
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

            _set_stage_completed(stage_status, "embedding", latency_ms=retrieval_ms, outcome="query_embedded")
            _set_stage_completed(
                stage_status,
                "retrieval",
                latency_ms=retrieval_ms,
                outcome="relevant_context_found" if len(retrieved_docs) > 0 else "no_relevant_context",
            )

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
            _set_stage_completed(
                stage_status,
                "llm_generation",
                latency_ms=llm_ms,
                outcome="generated" if (answer or "").strip() else "empty",
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
            fallback_mode = "fallback_after_pipeline_error"
            fallback_reason = str(exc)
            _set_stage_failed(stage_status, "retrieval", str(exc))
            _set_stage_failed(stage_status, "embedding", str(exc))
            _set_stage_failed(stage_status, "llm_generation", str(exc))
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
        _set_stage_completed(stage_status, "embedding", outcome="query_embedded")
    except Exception as exc:
        _set_stage_failed(stage_status, "embedding", str(exc))
        _set_stage_failed(stage_status, "retrieval", str(exc), outcome="retrieval_unavailable")
        if retrieval_stage:
            ops.end_span(retrieval_stage, error=str(exc))
        err_msg = f"Retrieval failed: {exc}"
        if root is not None:
            ops.end_root(root, error=err_msg, metrics={"overall_ms": round((time.perf_counter() - started) * 1000.0, 2), "stage_status": stage_status})
        raise HTTPException(status_code=502, detail=err_msg)
    retrieval_ms = round((time.perf_counter() - retrieval_start) * 1000.0, 2)
    _set_stage_completed(
        stage_status,
        "retrieval",
        latency_ms=retrieval_ms,
        outcome="relevant_context_found" if len(contexts) > 0 else "no_relevant_context",
    )
    if (stage_status.get("embedding") or {}).get("execution_status") != "Failed":
        _set_stage_completed(stage_status, "embedding", latency_ms=retrieval_ms, outcome="query_embedded")
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
        _set_stage_skipped(stage_status, "llm_generation", outcome="skipped_no_context")
        if answer:
            fallback_mode = fallback_mode or "llm_only_response"
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
            _set_stage_completed(
                stage_status,
                "llm_generation",
                latency_ms=llm_ms,
                outcome="generated" if (answer or "").strip() else "empty",
            )
        except TypeError:
            # Backward-compatibility fallback for older function signatures.
            llm_start = time.perf_counter()
            result = generate_answer_with_meta(question, contexts, [])
            llm_ms = round((time.perf_counter() - llm_start) * 1000.0, 2)
            answer = result.get("answer", "")
            prompt_text = result.get("prompt")
            token_usage = result.get("token_usage", token_usage)
            _set_stage_completed(
                stage_status,
                "llm_generation",
                latency_ms=llm_ms,
                outcome="generated" if (answer or "").strip() else "empty",
            )
        except Exception as exc:
            _set_stage_failed(stage_status, "llm_generation", str(exc))
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