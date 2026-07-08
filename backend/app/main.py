from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
import os

from app.config import CORS_ORIGINS, PDF_STORAGE_PATH, CHROMA_PATH, DB_PATH
from app.database import init_db
from app.routes import chat, document, ops
from app.ops.langsmith_ops import LangSmithOps
from app.rag.provider import LangChainRAG

app = FastAPI(title="RAG Backend")
app.state.langchain_rag = None
app.state.ops = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

    try:
        app.state.ops = LangSmithOps()
        if app.state.ops.enabled:
            print("[INFO] LangSmith observability enabled")
        else:
            print("[INFO] LangSmith observability disabled (set LANGSMITH_API_KEY)")
    except Exception as exc:
        app.state.ops = None
        print(f"[WARN] LangSmith observability unavailable: {exc}")

    try:
        app.state.langchain_rag = LangChainRAG()
        if app.state.langchain_rag.enabled:
            print("[INFO] LangChain enabled")
        else:
            print("[INFO] LangChain installed but disabled (set USE_LANGCHAIN=true)")
    except Exception as exc:
        app.state.langchain_rag = None
        print(f"[WARN] LangChain disabled: {exc}")

app.include_router(document.router)
app.include_router(chat.router)
app.include_router(ops.router)

@app.get("/health")
def health():
    return {"status": "ok"}
