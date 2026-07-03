from __future__ import annotations

import os
from typing import Optional, Any

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
        self._ensure_ready()
        docs = self._retriever.invoke(query or "")
        context = "\n\n".join(getattr(d, "page_content", "") for d in docs)
        prompt = (
            "Answer using only the provided context. "
            "If not in context, say you don't know.\n\n"
            f"Question: {query}\n\nContext:\n{context}"
        )
        resp = self._llm.invoke(prompt)
        return getattr(resp, "content", str(resp))