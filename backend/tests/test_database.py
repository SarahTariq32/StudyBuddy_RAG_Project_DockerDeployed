import sqlite3

from app import database


def test_connection():
    conn = database.get_connection()

    assert isinstance(conn, sqlite3.Connection)

    conn.close()


def test_init_db(mocker):
    conn = mocker.MagicMock()

    cursor = mocker.MagicMock()

    conn.cursor.return_value = cursor

    cursor.execute.return_value.fetchall.return_value = []

    mocker.patch(
        "app.database.get_connection",
        return_value=conn,
    )

    database.init_db()

    assert conn.commit.called
    assert conn.close.called


def test_row_factory():
    conn = database.get_connection()

    assert conn.row_factory == sqlite3.Row

    conn.close()