import os
import logging
from dotenv import load_dotenv, dotenv_values # type: ignore

# Get base directory of the backend application
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables normally
load_dotenv(os.path.join(_BASE_DIR, ".env"))

# Manually load the .env values as a dictionary to check for fallback values
# if environment variables are set to empty strings (e.g. by Docker Compose)
_env_file_vars = dotenv_values(os.path.join(_BASE_DIR, ".env"))

def get_env_var(name: str, default: str = "") -> str:
    """
    Retrieve environment variable, falling back to .env file values if the 
    variable is missing or set to an empty string in the system/container environment.
    """
    val = os.getenv(name)
    if val is None or val.strip() == "":
        val = _env_file_vars.get(name, "")
    if val is None or val.strip() == "":
        return default
    return val.strip()

# --- LLM Provider Selection ---
# This one variable controls which provider the entire app uses.
LLM_PROVIDER = get_env_var("LLM_PROVIDER", "groq")

# --- App Limits ---
MAX_PDFS = 5
MAX_FILE_SIZE_MB = int(get_env_var("MAX_FILE_SIZE_MB", "50"))

# --- Provider Credentials & Model Names ---
GEMINI_API_KEY = get_env_var("GEMINI_API_KEY", "")
GEMINI_MODEL = get_env_var("GEMINI_MODEL", "gemini-2.0-flash")

GROQ_API_KEY = get_env_var("GROQ_API_KEY", "")
GROQ_MODEL = get_env_var("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- OpenRouter ---
OPENROUTER_API_KEY = get_env_var("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = get_env_var("OPENROUTER_MODEL", "meta-llama/llama-3.3-8b-instruct:free")

# --- LangSmith / LLMOps ---
LANGSMITH_API_KEY = get_env_var("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = get_env_var("LANGSMITH_PROJECT", "studybuddy-rag")

# Warn if LangSmith API key is missing; dashboard will show disabled state.
if not LANGSMITH_API_KEY:
    import logging
    logging.warning("LANGSMITH_API_KEY is not set; LangSmith observability will be disabled.")

# --- Embedding Model ---
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_BATCH_SIZE = int(get_env_var("EMBEDDING_BATCH_SIZE", "48"))

# --- Chunking ---
# Larger chunks reduce total embedding calls and speed up indexing.
PARENT_CHUNK_SIZE = int(get_env_var("PARENT_CHUNK_SIZE", "1500"))
CHILD_CHUNK_SIZE = int(get_env_var("CHILD_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(get_env_var("CHUNK_OVERLAP", "50"))

# Hard cap to prevent very large PDFs from generating huge embedding workloads.
MAX_CHILD_CHUNKS = int(get_env_var("MAX_CHILD_CHUNKS", "450"))
MAX_PDF_PAGES = int(get_env_var("MAX_PDF_PAGES", "40"))
MAX_TEXT_CHARS = int(get_env_var("MAX_TEXT_CHARS", "120000"))
MAX_PARENT_TEXT_IN_METADATA = int(get_env_var("MAX_PARENT_TEXT_IN_METADATA", "1800"))

# --- Retrieval ---
TOP_K = 8
NUM_MULTI_QUERIES = int(get_env_var("NUM_MULTI_QUERIES", "3"))
MAX_CONTEXT_PARENTS = 15
DISTANCE_THRESHOLD = float(get_env_var("DISTANCE_THRESHOLD", "0.8"))
MIN_RELEVANCE_SCORE = float(get_env_var("MIN_RELEVANCE_SCORE", "0.30"))

# --- Conversation Memory ---
N_MESSAGES = 20
HISTORY_STRATEGY = 2

# --- Storage Paths ---
PDF_STORAGE_PATH = get_env_var("PDF_STORAGE_PATH", os.path.join(_BASE_DIR, "storage", "pdfs"))
CHROMA_PATH = get_env_var("CHROMA_PATH", os.path.join(_BASE_DIR, "storage", "chroma_db"))
DB_PATH = get_env_var("DB_PATH", os.path.join(_BASE_DIR, "storage", "app.db"))

# --- Optional Chroma Server Mode ---
# If CHROMA_HOST is set, backend will connect to a separate ChromaDB service
# (e.g., docker-compose service named "db") instead of local PersistentClient.
CHROMA_HOST = get_env_var("CHROMA_HOST", "").strip()
CHROMA_PORT = int(get_env_var("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = get_env_var("CHROMA_COLLECTION", "documents")

# --- CORS ---
# Comma-separated list, e.g. "https://my-frontend.vercel.app,http://localhost:5173"
CORS_ORIGINS = [o.strip() for o in get_env_var("CORS_ORIGINS", "*").split(",") if o.strip()]