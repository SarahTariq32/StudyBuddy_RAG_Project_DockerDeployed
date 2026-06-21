from datetime import datetime, timezone

from app.config import N_MESSAGES
from app.database import get_connection


def save_message(session_id: str, role: str, message: str) -> None:
    """Append one message to chat_history for this session."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_history (session_id, role, message, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, message, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_recent_history(session_id: str) -> list[dict]:
    """
    Return the last N_MESSAGES rows for this session, oldest first.
    Each item is {"role": ..., "message": ...}.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT role, message FROM chat_history
        WHERE session_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (session_id, N_MESSAGES),
    ).fetchall()
    conn.close()
    return [{"role": row["role"], "message": row["message"]} for row in reversed(rows)]
