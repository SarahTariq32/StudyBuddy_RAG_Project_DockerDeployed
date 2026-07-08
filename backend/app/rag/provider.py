from __future__ import annotations

import os
import time
from typing import Optional, Any
from app.config import NUM_MULTI_QUERIES, MIN_RELEVANCE_SCORE
from app.rag.query_rewrite import generate_multi_queries

try:
    from langchain_core.embeddings import Embeddings  # type: ignore
except Exception:  # pragma: no cover
    class Embeddings:
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            raise NotImplementedError

        def embed_query(self, text: str) -> list[float]:
            raise NotImplementedError

try:
    from app.rag.embeddings import create_embeddings as _create_embeddings
except Exception:  # pragma: no cover
    _create_embeddings = None


def _env(*keys: str, default: Optional[str] = None) -> Optional[str]:
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip() != "":
            return v
    return default


def _env_int(*keys: str, default: int) -> int:
    raw = _env(*keys, default=str(default))
    try:
        return int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default


def _create_vectors(texts: list[str]) -> list[list[float]]:
    if _create_embeddings is None:
        raise RuntimeError("Missing app.rag.embeddings.create_embeddings")
    return _create_embeddings(texts)


class LegacyEmbeddingsAdapter(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t for t in texts if isinstance(t, str) and t.strip()]
        if not cleaned:
            return []
        return [list(map(float, v)) for v in _create_vectors(cleaned)]

    def embed_query(self, text: str) -> list[float]:
        vectors = _create_vectors([text or " "])
        return list(map(float, vectors[0])) if vectors else []


class LangChainRAG:
    def __init__(self) -> None:
        self.enabled = (_env("USE_LANGCHAIN", default="false") or "false").lower() == "true"
        self.collection = _env("CHROMA_COLLECTION", default="documents") or "documents"
        self.persist_dir = _env("CHROMA_PERSIST_DIR", "CHROMA_PATH", default="./storage/chroma_db") or "./storage/chroma_db"
        self.chroma_host = _env("CHROMA_HOST")
        self.chroma_port = _env_int("CHROMA_PORT", default=8000)
        self.k = _env_int("RAG_TOP_K", default=8)

        self._embeddings: Any = None
        self._llm: Any = None
        self._vs: Any = None
        self._retriever: Any = None

    def _build_embeddings(self):
        provider = (_env("RAG_EMBEDDINGS_PROVIDER", default="legacy") or "legacy").lower()

        if provider in ("legacy", "onnx", "default"):
            return LegacyEmbeddingsAdapter()

        if provider in ("google", "gemini"):
            from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore
            return GoogleGenerativeAIEmbeddings(
                model=_env("GOOGLE_EMBEDDING_MODEL", default="models/text-embedding-004"),
                google_api_key=_env("GOOGLE_API_KEY", "GEMINI_API_KEY"),
            )

        from langchain_openai import OpenAIEmbeddings  # type: ignore
        return OpenAIEmbeddings(
            model=_env("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small"),
            api_key=_env("OPENAI_API_KEY"),
        )

    def _build_llm(self):
        provider = (_env("RAG_LLM_PROVIDER", "LLM_PROVIDER", default="groq") or "groq").lower()

        if provider in ("google", "gemini"):
            from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
            return ChatGoogleGenerativeAI(
                model=_env("GOOGLE_CHAT_MODEL", "GEMINI_MODEL", default="gemini-2.0-flash"),
                google_api_key=_env("GOOGLE_API_KEY", "GEMINI_API_KEY"),
                temperature=0,
            )

        if provider == "groq":
            from langchain_groq import ChatGroq  # type: ignore
            return ChatGroq(
                model=_env("GROQ_CHAT_MODEL", "GROQ_MODEL", default="llama-3.3-70b-versatile"),
                groq_api_key=_env("GROQ_API_KEY"),
                temperature=0,
            )

        from langchain_openai import ChatOpenAI  # type: ignore
        return ChatOpenAI(
            model=_env("OPENAI_CHAT_MODEL", default="gpt-4o-mini"),
            api_key=_env("OPENAI_API_KEY"),
            temperature=0,
        )

    def _ensure_ready(self) -> None:
        if self._embeddings is None:
            self._embeddings = self._build_embeddings()
        if self._llm is None:
            self._llm = self._build_llm()
        if self._vs is None:
            from langchain_chroma import Chroma  # type: ignore

            if self.chroma_host:
                import chromadb  # type: ignore

                client = chromadb.HttpClient(host=self.chroma_host, port=self.chroma_port)
                self._vs = Chroma(
                    client=client,
                    collection_name=self.collection,
                    embedding_function=self._embeddings,
                )
            else:
                self._vs = Chroma(
                    collection_name=self.collection,
                    persist_directory=self.persist_dir,
                    embedding_function=self._embeddings,
                )
        if self._retriever is None:
            self._retriever = self._vs.as_retriever(search_kwargs={"k": self.k})

    def answer(self, query: str) -> str:
        return self.answer_with_details(query).get("answer", "")

    @staticmethod
    def _looks_like_follow_up(question: str) -> bool:
        text = (question or "").strip().lower()
        if not text:
            return False
        words = [w.strip(".,!?;:\"'()[]{}") for w in text.split()]
        markers = {
            "it", "its", "that", "this", "those", "these", "they", "them",
            "he", "she", "there", "here", "again", "same", "above", "previous", "earlier",
            "mean", "means", "because", "why", "how", "what", "which", "who",
        }
        return len(words) <= 6 or any(w in markers for w in words)

    def _retrieve_with_scores(self, query: str) -> tuple[list[Any], list[dict], float]:
        """Return docs, scored metadata, and best relevance score for a single query."""
        scored_docs: list[tuple[Any, Any]] = []
        retrieved_documents: list[dict] = []
        best_score = 0.0

        try:
            scored_docs = self._vs.similarity_search_with_relevance_scores(query, k=max(self.k, 4))
        except Exception:
            return [], [], 0.0

        docs: list[Any] = []
        for doc, score in scored_docs:
            score_value = float(score) if score is not None else None
            if score_value is not None:
                best_score = max(best_score, score_value)
            if score_value is not None and score_value < float(MIN_RELEVANCE_SCORE):
                continue

            meta = getattr(doc, "metadata", {}) or {}
            docs.append(doc)
            retrieved_documents.append(
                {
                    "source": meta.get("source") or meta.get("doc_id") or "unknown",
                    "score": score_value,
                    "text_preview": getattr(doc, "page_content", "")[:240],
                }
            )

        return docs[: self.k], retrieved_documents[: self.k], best_score

    def answer_with_details(self, query: str) -> dict:
        self._ensure_ready()
        q = query or ""
        rewrites: list[str] = []

        retrieval_start = time.perf_counter()
        docs = []
        retrieved_documents: list[dict] = []
        best_score = 0.0
        try:
            docs, retrieved_documents, best_score = self._retrieve_with_scores(q)

            should_expand = (
                NUM_MULTI_QUERIES > 0
                and q.strip()
                and (len(docs) < 2 or best_score < (float(MIN_RELEVANCE_SCORE) + 0.10))
                and self._looks_like_follow_up(q)
            )

            if should_expand:
                try:
                    rewrites = generate_multi_queries(q, NUM_MULTI_QUERIES)
                except Exception:
                    rewrites = []

                dedupe_docs: dict[str, dict] = {}
                for doc in docs:
                    meta = getattr(doc, "metadata", {}) or {}
                    page_content = getattr(doc, "page_content", "")
                    key = f"{meta.get('source') or meta.get('doc_id') or 'unknown'}|{page_content[:160]}"
                    dedupe_docs[key] = {"doc": doc, "score": None}

                for rq in rewrites:
                    expanded_docs, expanded_meta, expanded_best = self._retrieve_with_scores(rq)
                    best_score = max(best_score, expanded_best)
                    for doc_item, meta_item in zip(expanded_docs, expanded_meta):
                        meta = getattr(doc_item, "metadata", {}) or {}
                        page_content = getattr(doc_item, "page_content", "")
                        key = f"{meta.get('source') or meta.get('doc_id') or 'unknown'}|{page_content[:160]}"
                        dedupe_docs[key] = {"doc": doc_item, "score": meta_item.get("score")}

                merged = sorted(
                    [(item["doc"], item["score"]) for item in dedupe_docs.values()],
                    key=lambda x: float(x[1] if x[1] is not None else -1.0),
                    reverse=True,
                )[: self.k]
                docs = [d for d, _ in merged]

                retrieved_documents = []
                for doc, score in merged:
                    meta = getattr(doc, "metadata", {}) or {}
                    retrieved_documents.append(
                        {
                            "source": meta.get("source") or meta.get("doc_id") or "unknown",
                            "score": float(score) if score is not None else None,
                            "text_preview": getattr(doc, "page_content", "")[:240],
                        }
                    )
        except Exception:
            docs = []
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000.0

        if not retrieved_documents:
            for doc in docs:
                meta = getattr(doc, "metadata", {}) or {}
                retrieved_documents.append(
                    {
                        "source": meta.get("source") or meta.get("doc_id") or "unknown",
                        "score": None,
                        "text_preview": getattr(doc, "page_content", "")[:240],
                    }
                )

        context = "\n\n".join(getattr(d, "page_content", "") for d in docs)

        if not docs:
            return {
                "answer": "I could not find relevant evidence in your uploaded documents for this question.",
                "prompt": "",
                "rewrites": rewrites,
                "multi_query_used": bool(rewrites),
                "retrieved_documents": [],
                "retrieved_chunk_count": 0,
                "token_usage": {
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                },
                "latency_ms": {
                    "retrieval_ms": round(retrieval_ms, 2),
                    "llm_ms": None,
                },
            }

        prompt = (
            "Answer using only the provided context. "
            "If not in context, say you don't know.\n\n"
            f"Question: {q}\n\nContext:\n{context}"
        )

        llm_start = time.perf_counter()
        resp = self._llm.invoke(prompt)
        llm_ms = (time.perf_counter() - llm_start) * 1000.0

        usage_meta = getattr(resp, "usage_metadata", {}) or {}
        if not usage_meta:
            usage_meta = getattr(resp, "response_metadata", {}).get("token_usage", {}) or {}

        answer = getattr(resp, "content", str(resp))
        return {
            "answer": answer,
            "prompt": prompt,
            "rewrites": rewrites,
            "multi_query_used": bool(rewrites),
            "min_relevance_score": float(MIN_RELEVANCE_SCORE),
            "retrieved_documents": retrieved_documents,
            "retrieved_chunk_count": len(retrieved_documents),
            "token_usage": {
                "input_tokens": usage_meta.get("input_tokens") or usage_meta.get("prompt_tokens"),
                "output_tokens": usage_meta.get("output_tokens") or usage_meta.get("completion_tokens"),
                "total_tokens": usage_meta.get("total_tokens"),
            },
            "latency_ms": {
                "retrieval_ms": round(retrieval_ms, 2),
                "llm_ms": round(llm_ms, 2),
            },
        }