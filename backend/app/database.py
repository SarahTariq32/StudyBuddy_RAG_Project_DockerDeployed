import os
import sqlite3
from app.config import DB_PATH


def get_connection():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'uploaded',
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            content_hash TEXT
        )
        """
    )

    # --- migrations for old DBs ---
    doc_cols = cur.execute("PRAGMA table_info(documents)").fetchall()
    cols = {row["name"] for row in doc_cols}

    # Older schema used INTEGER autoincrement IDs while current code uses UUID strings.
    # Rebuild the table once so uploads do not fail with type mismatch.
    id_col = next((row for row in doc_cols if row["name"] == "id"), None)
    id_type = (id_col["type"] or "").upper() if id_col else ""
    if id_type != "TEXT":
        cur.execute(
            """
            CREATE TABLE documents_new (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'uploaded',
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT
            )
            """
        )

        if "uploaded_at" in cols and "content_hash" in cols:
            cur.execute(
                """
                INSERT INTO documents_new (id, filename, status, uploaded_at, content_hash)
                SELECT CAST(id AS TEXT), filename, status, uploaded_at, content_hash
                FROM documents
                """
            )
        elif "uploaded_at" in cols:
            cur.execute(
                """
                INSERT INTO documents_new (id, filename, status, uploaded_at)
                SELECT CAST(id AS TEXT), filename, status, uploaded_at
                FROM documents
                """
            )
        else:
            # Legacy fallback for very old schema variants.
            cur.execute(
                """
                INSERT INTO documents_new (id, filename, status, uploaded_at)
                SELECT CAST(id AS TEXT), filename, status, COALESCE(created_at, CURRENT_TIMESTAMP)
                FROM documents
                """
            )

        cur.execute("DROP TABLE documents")
        cur.execute("ALTER TABLE documents_new RENAME TO documents")
        cols = {row["name"] for row in cur.execute("PRAGMA table_info(documents)").fetchall()}

    if "uploaded_at" not in cols:
        cur.execute("ALTER TABLE documents ADD COLUMN uploaded_at TEXT")

    if "content_hash" not in cols:
        cur.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT")

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash)"
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()