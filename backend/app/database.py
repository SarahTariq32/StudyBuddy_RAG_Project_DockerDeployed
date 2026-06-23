import sqlite3
from app.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ready' ,                
            
            content_hash TEXT
        )
    """)
    # Ensure content_hash exists for older DBs
    cols = [row["name"] for row in cursor.execute("PRAGMA table_info(documents)").fetchall()]
    if "content_hash" not in cols:
        cursor.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT")

    # Enforce dedupe at DB level (NULLs allowed, non-NULL must be unique)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_content_hash
        ON documents(content_hash)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()