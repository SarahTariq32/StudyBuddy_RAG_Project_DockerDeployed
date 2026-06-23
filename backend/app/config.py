import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Provider Selection ---
# This one variable controls which provider the entire app uses.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

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

# --- Chunking ---
# Larger chunks reduce total embedding calls and speed up indexing.
PARENT_CHUNK_SIZE = int(os.getenv("PARENT_CHUNK_SIZE", "1500"))
CHILD_CHUNK_SIZE = int(os.getenv("CHILD_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Hard cap to prevent very large PDFs from generating huge embedding workloads.
MAX_CHILD_CHUNKS = int(os.getenv("MAX_CHILD_CHUNKS", "1200"))
# Cap extraction/indexing work for very large files.
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "80"))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "250000"))

# --- Retrieval ---
TOP_K = 3
# 0 = skip multi-query rewrite (fastest). 4 = better recall, slower (extra LLM call).
NUM_MULTI_QUERIES = 0
MAX_CONTEXT_PARENTS = 10

# --- Conversation Memory ---
N_MESSAGES = 5
HISTORY_STRATEGY = 2

# --- App Limits ---
MAX_PDFS = 5

# --- Storage Paths ---
PDF_STORAGE_PATH = "storage/pdfs"
CHROMA_PATH = "storage/chroma_db"
DB_PATH = "app.db"