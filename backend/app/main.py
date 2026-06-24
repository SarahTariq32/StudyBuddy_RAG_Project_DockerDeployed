from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.config import CORS_ORIGINS, PDF_STORAGE_PATH, CHROMA_PATH, DB_PATH
from app.routes import chat, document
from app.llm.factory import get_llm_client
import os

app = FastAPI(title="RAG Backend")

# --- CORS ---
# The browser blocks requests from one origin (e.g. localhost:5173) to another
# (localhost:8000) unless the server explicitly allows it. This middleware adds
# the necessary headers. allow_origins=["*"] is fine for local dev; tighten it
# to your deployed frontend URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB init ---
# Create tables on startup if they don't exist yet. This is idempotent:
# running it twice does nothing because of "CREATE TABLE IF NOT EXISTS".
@app.on_event("startup")
def startup():
    # Ensure storage directories exist (important when using persistent volumes
    # where sub-directories may not be pre-created).
    os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
    os.makedirs(CHROMA_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    init_db()
    print("✓ Database initialized")

    # Any document that was left in 'processing' state from a previous server
    # run (e.g. the indexing thread was killed mid-way during a redeploy) will
    # never complete. Mark them as 'error' so users know to re-upload.
    from app.database import get_connection
    conn = get_connection()
    stuck = conn.execute(
        "SELECT COUNT(*) FROM documents WHERE status = 'processing'"
    ).fetchone()[0]
    if stuck:
        conn.execute("UPDATE documents SET status = 'error' WHERE status = 'processing'")
        conn.commit()
        print(f"⚠ Reset {stuck} stuck 'processing' document(s) to 'error' on startup")
    conn.close()

    get_llm_client()
    print("✓ LLM provider initialized")


app.include_router(document.router)
app.include_router(chat.router)


# --- Health check ---
@app.get("/health")
def health():
    return {"status": "ok"}
