import io
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.routes import document
from app.schemas import DocumentRenameRequest


# -----------------------------
# Upload Validation
# -----------------------------

def test_upload_rejects_non_pdf(client):
    response = client.post(
        "/documents",
        files={"file": ("hello.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]


def test_document_exists_false(mocker):
    conn = MagicMock()

    conn.execute.return_value.fetchone.return_value = None

    mocker.patch(
        "app.routes.document.get_connection",
        return_value=conn,
    )

    assert document._document_exists("abc") is False


def test_document_exists_true(mocker):
    conn = MagicMock()

    conn.execute.return_value.fetchone.return_value = {"id": "abc"}

    mocker.patch(
        "app.routes.document.get_connection",
        return_value=conn,
    )

    assert document._document_exists("abc") is True


# -----------------------------
# Rename Validation
# -----------------------------

import pytest
from pydantic import ValidationError

def test_empty_filename():
    with pytest.raises(ValidationError):
        DocumentRenameRequest(filename="")

def test_filename_too_long():
    with pytest.raises(ValidationError):
        DocumentRenameRequest(filename="a" * 260)

def test_invalid_filename():
    body = DocumentRenameRequest(filename="folder/test.pdf")

    with pytest.raises(HTTPException):
        document._rename_document_impl("123", body)


def test_pdf_extension_added(mocker):
    row = {
        "id": "1",
        "filename": "old.pdf",
        "uploaded_at": "today",
        "status": "ready",
    }

    updated = {
        "id": "1",
        "filename": "new.pdf",
        "uploaded_at": "today",
        "status": "ready",
    }

    conn = MagicMock()

    conn.execute.side_effect = [
        MagicMock(fetchone=lambda: row),
        MagicMock(),
        MagicMock(fetchone=lambda: updated),
    ]

    mocker.patch(
        "app.routes.document.get_connection",
        return_value=conn,
    )

    body = DocumentRenameRequest(filename="new")

    result = document._rename_document_impl("1", body)

    assert result.filename == "new.pdf"


# -----------------------------
# Cleanup
# -----------------------------

def test_cleanup_deleted_document(mocker):
    delete_mock = mocker.patch(
        "app.routes.document.vector_store.delete_document"
    )

    exists_mock = mocker.patch(
        "app.routes.document.os.path.exists",
        return_value=True,
    )

    remove_mock = mocker.patch(
        "app.routes.document.os.remove"
    )

    document._cleanup_deleted_document(
        "abc",
        "/tmp/test.pdf",
    )

    delete_mock.assert_called_once_with("abc")

    exists_mock.assert_called_once()

    remove_mock.assert_called_once()


# -----------------------------
# Delete Validation
# -----------------------------

def test_delete_missing_document(client, mocker):
    conn = MagicMock()

    conn.execute.return_value.fetchone.return_value = None

    mocker.patch(
        "app.routes.document.get_connection",
        return_value=conn,
    )

    response = client.delete("/documents/123")

    assert response.status_code == 404


# -----------------------------
# Listing
# -----------------------------

def test_list_documents_empty(client, mocker):
    conn = MagicMock()

    conn.execute.return_value.fetchall.return_value = []

    mocker.patch(
        "app.routes.document.get_connection",
        return_value=conn,
    )

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == []