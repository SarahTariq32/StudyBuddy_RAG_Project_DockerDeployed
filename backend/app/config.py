import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Provider Selection ---
# This one variable controls which provider the entire app uses.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

# --- App Limits ---
MAX_PDFS = 5
# Maximum PDF upload size in megabytes.
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

# --- Provider Credentials & Model Names ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# --- OpenRouter ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-8b-instruct:free")
# --- Embedding Model ---
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "48"))

# --- Chunking ---
# Larger chunks reduce total embedding calls and speed up indexing.
PARENT_CHUNK_SIZE = int(os.getenv("PARENT_CHUNK_SIZE", "1500"))
CHILD_CHUNK_SIZE = int(os.getenv("CHILD_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Hard cap to prevent very large PDFs from generating huge embedding workloads.
MAX_CHILD_CHUNKS = int(os.getenv("MAX_CHILD_CHUNKS", "450"))
# Cap extraction/indexing work for very large files.
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "40"))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "120000"))
# Reduce write amplification in vector metadata.
MAX_PARENT_TEXT_IN_METADATA = int(os.getenv("MAX_PARENT_TEXT_IN_METADATA", "1800"))

# --- Retrieval ---
TOP_K = 8
# 0 = skip multi-query rewrite (fastest). 4 = better recall, slower (extra LLM call).
# Set to 2 for better semantic coverage across query variants.
NUM_MULTI_QUERIES = 2
MAX_CONTEXT_PARENTS = 15
# L2 distance cutoff for chunk relevance (DefaultEmbeddingFunction produces
# unit-norm vectors, so L2 range is 0–√2 ≈ 1.414).
# 1.0  ≈ cosine similarity ≥ 0.50 (relevant)
# 1.2  ≈ cosine similarity ≥ 0.28 (loosely related)
# Keep at 1.2 so we never drop valid context from short/broad questions.
DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", "1.2"))

# --- Conversation Memory ---
N_MESSAGES = 5
HISTORY_STRATEGY = 2

# --- Storage Paths ---
# Override these in production to point at a persistent volume, e.g.:
#   PDF_STORAGE_PATH=/data/pdfs
#   CHROMA_PATH=/data/chroma_db
#   DB_PATH=/data/app.db
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", os.path.join(_BASE_DIR, "storage", "pdfs"))
CHROMA_PATH = os.getenv("CHROMA_PATH", os.path.join(_BASE_DIR, "storage", "chroma_db"))
DB_PATH = os.getenv("DB_PATH", os.path.join(_BASE_DIR, "storage", "app.db"))

# --- CORS ---
# Comma-separated list, e.g. "https://my-frontend.vercel.app,http://localhost:5173"
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]