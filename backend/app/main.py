from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routes import chat, document

app = FastAPI(title="RAG Backend")

# --- CORS ---
# The browser blocks requests from one origin (e.g. localhost:5173) to another
# (localhost:8000) unless the server explicitly allows it. This middleware adds
# the necessary headers. allow_origins=["*"] is fine for local dev; tighten it
# to your deployed frontend URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB init ---
# Create tables on startup if they don't exist yet. This is idempotent:
# running it twice does nothing because of "CREATE TABLE IF NOT EXISTS".
@app.on_event("startup")
def startup():
    init_db()
    print("✓ Database initialized")


app.include_router(document.router)
app.include_router(chat.router)


# --- Health check ---
@app.get("/health")
def health():
    return {"status": "ok"}
