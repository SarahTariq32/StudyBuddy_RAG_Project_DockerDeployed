import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Provider Selection ---
# This one variable controls which provider the entire app uses.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# --- Provider Credentials & Model Names ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Embedding Model ---
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# --- Chunking ---
PARENT_CHUNK_SIZE = 1000
CHILD_CHUNK_SIZE = 300
CHUNK_OVERLAP = 100

# --- Retrieval ---
TOP_K = 3
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