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
    Return recent history oldest->newest.
    N_MESSAGES is treated as number of user turns, so fetch up to 2*N_MESSAGES rows.
    """
    limit_rows = max(2, N_MESSAGES * 2)

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT role, message
        FROM chat_history
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit_rows),
    ).fetchall()
    conn.close()

    return [{"role": row["role"], "message": row["message"]} for row in reversed(rows)]