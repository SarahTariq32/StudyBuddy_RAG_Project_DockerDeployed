from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.config import LLM_PROVIDER


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _to_ms(start: Any, end: Any) -> Optional[float]:
    if not start or not end:
        return None
    if isinstance(start, str):
        start = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if isinstance(end, str):
        end = datetime.fromisoformat(end.replace("Z", "+00:00"))
    if isinstance(start, datetime) and isinstance(end, datetime):
        return max(0.0, (end - start).total_seconds() * 1000.0)
    return None


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class TraceSpan:
    def __init__(self, trace_id: uuid.UUID, parent_id: Optional[uuid.UUID], name: str):
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.name = name
        self.start = _utcnow()


class LangSmithOps:
    """LangSmith tracing + dashboard data adapter.

    This is intentionally fail-open so the main RAG flow is never blocked by
    observability errors.
    """

    def __init__(self) -> None:
        self.client = None
        self.enabled = False
        self.project = "studybuddy-rag"
        self.public_enabled = False
        self._local_traces: list[dict] = []
        self._remote_traces_cache: list[dict] = []
        self._last_remote_sync_at: Optional[datetime] = None
        self._remote_sync_interval_seconds = 10  # faster sync for dashboard freshness
        self._cached_dashboard: dict = {
            "enabled": False,
            "project": "studybuddy-rag",
            "window_hours": 24,
            "active_provider": LLM_PROVIDER,
            "metrics": {},
            "charts": {},
            "recent_requests": [],
        }
        self._cached_traces: dict = {
            "enabled": False,
            "project": "studybuddy-rag",
            "count": 0,
            "traces": [],
        }
        self._init_client()

    def record_local_trace(self, trace: dict) -> None:
        """Store a lightweight recent trace for fast dashboard rendering."""
        if not isinstance(trace, dict):
            return
        trace_id = str(trace.get("id") or "")
        if trace_id:
            self._local_traces = [t for t in self._local_traces if str(t.get("id") or "") != trace_id]
        self._local_traces.insert(0, trace)
        self._local_traces = self._local_traces[:200]

    def _merged_recent_traces(self, remote_traces: list[dict], limit: int) -> list[dict]:
        merged: list[dict] = []
        seen: set[str] = set()

        for t in (self._local_traces + (remote_traces or [])):
            trace_id = str(t.get("id") or "")
            if trace_id and trace_id in seen:
                continue
            if trace_id:
                seen.add(trace_id)
            merged.append(t)
            if len(merged) >= max(1, int(limit)):
                break

        merged.sort(key=lambda t: t.get("timestamp") or "", reverse=True)
        return merged

    def _should_sync_remote(self) -> bool:
        if self._last_remote_sync_at is None:
            return True
        return (_utcnow() - self._last_remote_sync_at).total_seconds() >= self._remote_sync_interval_seconds

    def _get_remote_traces(self, *, hours: int, limit: int) -> list[dict]:
        if not self.enabled:
            return []

        if not self._should_sync_remote() and self._remote_traces_cache:
            return self._remote_traces_cache

        runs = self._iter_root_runs(hours=hours, limit=limit)
        if not runs:
            # Keep serving the last successful snapshot to avoid dashboard stalls.
            return self._remote_traces_cache

        formatted = [self._format_trace(r, include_children=False) for r in runs]
        formatted.sort(key=lambda t: t.get("timestamp") or "", reverse=True)
        self._remote_traces_cache = formatted
        self._last_remote_sync_at = _utcnow()
        return self._remote_traces_cache

    def _ensure_project_exists(self) -> None:
        if not self.enabled or self.client is None:
            return
        try:
            # list_projects returns an iterator; creating only if missing avoids
            # noisy errors when the project already exists.
            existing = {str(_safe_get(p, "name", "")) for p in self.client.list_projects()}
            if self.project not in existing:
                self.client.create_project(project_name=self.project)
                print(f"✓ LangSmith project created: {self.project}")
        except Exception as exc:
            print(f"LangSmith project ensure failed: {exc}")

    def _init_client(self) -> None:
        try:
            from langsmith import Client  # type: ignore
            from app.config import LANGSMITH_API_KEY, LANGSMITH_PROJECT

            self.project = LANGSMITH_PROJECT
            self.public_enabled = bool(LANGSMITH_API_KEY)
            if not LANGSMITH_API_KEY:
                return

            self.client = Client(api_key=LANGSMITH_API_KEY)
            self.enabled = True
        except Exception as exc:
            self.enabled = False
            self.client = None
            print(f"LangSmith init disabled: {exc}")

    def start_root_trace(self, *, question: str, session_id: str, path: str) -> TraceSpan:
        trace = TraceSpan(trace_id=uuid.uuid4(), parent_id=None, name="rag_request")
        if not self.enabled or self.client is None:
            return trace

        try:
            self.client.create_run(
                id=trace.trace_id,
                name="rag_request",
                run_type="chain",
                project_name=self.project,
                start_time=trace.start,
                inputs={"question": question, "session_id": session_id, "path": path},
                extra={
                    "metadata": {
                        "service": "studybuddy-backend",
                        "llm_provider": LLM_PROVIDER,
                    }
                },
                tags=["studybuddy", "rag", "request"],
            )
        except Exception as exc:
            print(f"LangSmith root create failed: {exc}")
        return trace

    def start_stage(self, root: TraceSpan, name: str, *, run_type: str = "chain", inputs: Optional[dict] = None) -> TraceSpan:
        stage = TraceSpan(trace_id=uuid.uuid4(), parent_id=root.trace_id, name=name)
        if not self.enabled or self.client is None:
            return stage

        try:
            self.client.create_run(
                id=stage.trace_id,
                parent_run_id=stage.parent_id,
                name=name,
                run_type=run_type,
                project_name=self.project,
                start_time=stage.start,
                inputs=inputs or {},
                extra={"metadata": {"stage": name}},
                tags=["studybuddy", "rag", "stage"],
            )
        except Exception as exc:
            print(f"LangSmith stage create failed ({name}): {exc}")

        return stage

    def end_span(self, span: TraceSpan, *, outputs: Optional[dict] = None, error: Optional[str] = None, extra: Optional[dict] = None) -> None:
        if not self.enabled or self.client is None:
            return

        payload: dict[str, Any] = {"end_time": _utcnow()}
        if outputs is not None:
            payload["outputs"] = outputs
        if error:
            payload["error"] = error
        if extra:
            payload["extra"] = extra

        try:
            self.client.update_run(span.trace_id, **payload)
        except Exception as exc:
            print(f"LangSmith update failed ({span.name}): {exc}")

    def end_root(self, root: TraceSpan, *, outputs: Optional[dict] = None, error: Optional[str] = None, metrics: Optional[dict] = None) -> None:
        self.end_span(root, outputs=outputs, error=error, extra={"metrics": metrics or {}})

    def _iter_root_runs(self, *, hours: int, limit: int):
        if not self.enabled or self.client is None:
            return []

        start_time = _utcnow() - timedelta(hours=max(1, int(hours)))
        try:
            return list(
                self.client.list_runs(
                    project_name=self.project,
                    is_root=True,
                    start_time=start_time,
                    limit=max(1, int(limit)),
                )
            )
        except Exception as exc:
            msg = str(exc)
            if "Project" in msg and "not found" in msg:
                self._ensure_project_exists()
                try:
                    return list(
                        self.client.list_runs(
                            project_name=self.project,
                            is_root=True,
                            start_time=start_time,
                            limit=max(1, int(limit)),
                        )
                    )
                except Exception as retry_exc:
                    print(f"LangSmith list runs retry failed: {retry_exc}")
                    return []
            print(f"LangSmith list runs failed: {exc}")
            return []

    def _iter_child_runs(self, root_id: str, *, limit: int = 200):
        if not self.enabled or self.client is None:
            return []

        try:
            return list(
                self.client.list_runs(
                    project_name=self.project,
                    filter=f'and(eq(parent_run_id,"{root_id}"))',
                    limit=max(1, int(limit)),
                )
            )
        except Exception:
            return []

    def _extract_token_usage(self, run_obj: Any) -> dict:
        outputs = _safe_get(run_obj, "outputs", {}) or {}
        usage = outputs.get("token_usage") if isinstance(outputs, dict) else None
        if isinstance(usage, dict):
            return {
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "total_tokens": usage.get("total_tokens"),
            }

        usage_meta = _safe_get(run_obj, "extra", {}) or {}
        nested = usage_meta.get("usage") if isinstance(usage_meta, dict) else None
        if isinstance(nested, dict):
            return {
                "input_tokens": nested.get("input_tokens"),
                "output_tokens": nested.get("output_tokens"),
                "total_tokens": nested.get("total_tokens"),
            }

        return {"input_tokens": None, "output_tokens": None, "total_tokens": None}

    def _format_trace(self, root: Any, *, include_children: bool = True) -> dict:
        root_id = str(_safe_get(root, "id", ""))
        start = _safe_get(root, "start_time")
        end = _safe_get(root, "end_time")
        inputs = _safe_get(root, "inputs", {}) or {}
        outputs = _safe_get(root, "outputs", {}) or {}
        error = _safe_get(root, "error")
        extra = _safe_get(root, "extra", {}) or {}

        stage_map: dict[str, dict] = {}
        retrieved_docs = []

        if include_children:
            children = self._iter_child_runs(root_id)
            for child in children:
                name = _safe_get(child, "name", "stage")
                c_inputs = _safe_get(child, "inputs", {}) or {}
                c_outputs = _safe_get(child, "outputs", {}) or {}
                c_error = _safe_get(child, "error")

                if name == "retrieval" and isinstance(c_outputs, dict):
                    retrieved_docs = c_outputs.get("retrieved_documents", []) or []

                stage_map[name] = {
                    "status": "failed" if c_error else "success",
                    "latency_ms": _to_ms(_safe_get(child, "start_time"), _safe_get(child, "end_time")),
                    "inputs": c_inputs,
                    "outputs": c_outputs,
                    "error": c_error,
                }

        metrics = extra.get("metrics", {}) if isinstance(extra, dict) else {}
        stage_status_metrics = metrics.get("stage_status", {}) if isinstance(metrics, dict) else {}

        if not stage_map and isinstance(stage_status_metrics, dict) and stage_status_metrics:
            for stage_name in ("query_rewrite", "retrieval", "prompt_creation", "llm_generation", "final_answer"):
                status_val = stage_status_metrics.get(stage_name)
                if not status_val:
                    continue
                latency_val = None
                if stage_name == "retrieval":
                    latency_val = metrics.get("retrieval_ms")
                elif stage_name == "llm_generation":
                    latency_val = metrics.get("llm_ms")
                stage_map[stage_name] = {
                    "status": status_val,
                    "latency_ms": latency_val,
                    "inputs": {},
                    "outputs": {},
                    "error": None,
                }

        token_usage = self._extract_token_usage(root)
        query_stage = (stage_map.get("query_rewrite", {}) or {})
        query_stage_inputs = query_stage.get("inputs", {}) if isinstance(query_stage, dict) else {}
        query_stage_outputs = query_stage.get("outputs", {}) if isinstance(query_stage, dict) else {}
        question_value = inputs.get("question") or query_stage_inputs.get("question") or query_stage_inputs.get("query")
        rewrite_value = (
            query_stage_outputs.get("rewritten_question")
            or query_stage_outputs.get("query_rewrite")
            or outputs.get("query_rewrite")
            or question_value
        )
        final_stage_outputs = (stage_map.get("final_answer", {}).get("outputs", {}) or {}) if isinstance(stage_map, dict) else {}
        answer_outcome = final_stage_outputs.get("outcome") or outputs.get("answer_outcome")
        final_stage_failed = (stage_map.get("final_answer", {}).get("status") == "failed") if isinstance(stage_map, dict) else False
        resolved_status = "failed" if error or final_stage_failed else "success"
        retrieved_chunk_count = len(retrieved_docs)
        if retrieved_chunk_count == 0:
            retrieved_chunk_count = (
                metrics.get("retrieved_chunk_count")
                or outputs.get("retrieved_chunk_count")
                or 0
            )

        return {
            "id": root_id,
            "timestamp": _to_iso(start),
            "status": resolved_status,
            "question": question_value,
            "session_id": inputs.get("session_id"),
            "query_rewrite": rewrite_value,
            "answer_outcome": answer_outcome,
            "multi_queries": (stage_map.get("multi_query_generation", {}).get("outputs", {}) or {}).get("queries", []),
            "retrieved_documents": retrieved_docs,
            "retrieved_chunk_count": int(retrieved_chunk_count),
            "prompt_preview": (stage_map.get("prompt_creation", {}).get("outputs", {}) or {}).get("prompt_preview") or outputs.get("prompt_preview"),
            "llm_response_preview": (stage_map.get("llm_generation", {}).get("outputs", {}) or {}).get("answer_preview") or outputs.get("answer"),
            "token_usage": token_usage,
            "pipeline_stages": stage_map,
            "durations_ms": {
                "retrieval_ms": metrics.get("retrieval_ms") or (stage_map.get("retrieval", {}).get("latency_ms")),
                "llm_ms": metrics.get("llm_ms") or (stage_map.get("llm_generation", {}).get("latency_ms")),
                "overall_ms": metrics.get("overall_ms") or _to_ms(start, end),
            },
            "error": error,
        }

    def get_dashboard_data(self, *, hours: int = 24, limit: int = 100) -> dict:
        fast_limit = min(max(1, int(limit)), 50)
        remote_traces = self._get_remote_traces(hours=hours, limit=fast_limit)
        if not remote_traces and not self._local_traces:
            cached = dict(self._cached_dashboard)
            cached["enabled"] = self.public_enabled
            cached["project"] = self.project
            cached["window_hours"] = hours
            return cached

        # Combine local recent traces with remote traces for up‑to‑date dashboard
        all_traces = self._local_traces + (remote_traces or [])
        traces = self._merged_recent_traces(all_traces, max(20, fast_limit))

        total = len(traces)
        successes = sum(1 for t in traces if t.get("status") == "success")
        failures = total - successes

        def _avg(values: list[Optional[float]]) -> Optional[float]:
            clean = [float(v) for v in values if v is not None]
            if not clean:
                return None
            return sum(clean) / len(clean)

        avg_response_ms = _avg([t.get("durations_ms", {}).get("overall_ms") for t in traces])
        avg_retrieval_ms = _avg([t.get("durations_ms", {}).get("retrieval_ms") for t in traces])
        avg_llm_ms = _avg([t.get("durations_ms", {}).get("llm_ms") for t in traces])

        token_total = 0
        token_input = 0
        token_output = 0
        token_points = []

        per_day: dict[str, int] = {}
        latency_points = []
        retrieval_points = []

        for t in traces:
            stamp = t.get("timestamp")
            day = stamp[:10] if isinstance(stamp, str) and len(stamp) >= 10 else "unknown"
            per_day[day] = per_day.get(day, 0) + 1

            overall = t.get("durations_ms", {}).get("overall_ms")
            retrieval = t.get("durations_ms", {}).get("retrieval_ms")
            if overall is not None:
                latency_points.append({"timestamp": stamp, "value": round(float(overall), 2)})
            if retrieval is not None:
                retrieval_points.append({"timestamp": stamp, "value": round(float(retrieval), 2)})

            usage = t.get("token_usage", {}) or {}
            i_tok = usage.get("input_tokens")
            o_tok = usage.get("output_tokens")
            tot_tok = usage.get("total_tokens")

            if isinstance(i_tok, (int, float)):
                token_input += int(i_tok)
            if isinstance(o_tok, (int, float)):
                token_output += int(o_tok)
            if isinstance(tot_tok, (int, float)):
                token_total += int(tot_tok)
                token_points.append({"timestamp": stamp, "value": int(tot_tok)})

        recent = traces[:20]

        result = {
            "enabled": self.public_enabled,
            "project": self.project,
            "window_hours": hours,
            "active_provider": LLM_PROVIDER,
            "metrics": {
                "total_questions": total,
                "successful_requests": successes,
                "failed_requests": failures,
                "error_count": failures,
                "avg_response_time_ms": avg_response_ms,
                "avg_retrieval_time_ms": avg_retrieval_ms,
                "avg_llm_generation_time_ms": avg_llm_ms,
                "avg_retrieved_chunks": _avg([float(t.get("retrieved_chunk_count") or 0) for t in traces]),
                "token_usage": {
                    "input_tokens": token_input,
                    "output_tokens": token_output,
                    "total_tokens": token_total,
                },
            },
            "charts": {
                "response_time_over_time": list(reversed(latency_points[-100:])),
                "token_usage_over_time": list(reversed(token_points[-100:])),
                "questions_per_day": [{"day": k, "count": v} for k, v in sorted(per_day.items())],
                "success_failure": [
                    {"label": "success", "value": successes},
                    {"label": "failure", "value": failures},
                ],
                "retrieval_latency_trend": list(reversed(retrieval_points[-100:])),
            },
            "recent_requests": recent,
        }
        self._cached_dashboard = result
        return result

    def get_traces(self, *, hours: int = 24, limit: int = 30) -> dict:
        fast_limit = min(max(1, int(limit)), 50)
        remote_traces = self._get_remote_traces(hours=hours, limit=fast_limit)
        if not remote_traces and self.enabled and not self._local_traces:
            cached = dict(self._cached_traces)
            cached["enabled"] = self.public_enabled
            cached["project"] = self.project
            return cached

        traces = self._merged_recent_traces(remote_traces, fast_limit)
        result = {
            "enabled": self.public_enabled,
            "project": self.project,
            "count": len(traces),
            "traces": traces,
        }
        self._cached_traces = result
        return result

    def get_trace(self, trace_id: str) -> dict:
        # Prefer rich cached/local data; otherwise keep a fallback while hydrating detail.
        cached_fallback = None

        for trace in self._local_traces:
            if str(trace.get("id") or "") == str(trace_id):
                stage_map = trace.get("pipeline_stages") or {}
                if stage_map:
                    return {
                        "enabled": self.public_enabled,
                        "project": self.project,
                        "trace": trace,
                    }
                cached_fallback = trace
                break

        for trace in self._remote_traces_cache:
            if str(trace.get("id") or "") == str(trace_id):
                stage_map = trace.get("pipeline_stages") or {}
                if stage_map:
                    return {
                        "enabled": self.public_enabled,
                        "project": self.project,
                        "trace": trace,
                    }
                cached_fallback = cached_fallback or trace
                break

        if not self.enabled or self.client is None:
            return {
                "enabled": self.public_enabled,
                "project": self.project,
                "trace": cached_fallback,
            }

        try:
            run = self.client.read_run(trace_id)
            return {
                "enabled": self.public_enabled,
                "project": self.project,
                "trace": self._format_trace(run, include_children=True),
            }
        except Exception as exc:
            return {
                "enabled": self.public_enabled,
                "project": self.project,
                "trace": cached_fallback,
                "error": str(exc),
            }
