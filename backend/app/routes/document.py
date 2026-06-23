
import os
import uuid
from datetime import datetime, timezone
from threading import Thread

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.config import MAX_PDFS, PDF_STORAGE_PATH, PARENT_CHUNK_SIZE, CHILD_CHUNK_SIZE, CHUNK_OVERLAP
from app.database import get_connection
# from app.schemas import DocumentOut
from app.schemas import DocumentOut, DocumentRenameRequest
from app.rag.loader import load_single_pdf
from app.rag.chunking import create_parent_chunks, create_child_chunks
from app.rag.embeddings import create_embeddings
from app.rag import vector_store
import hashlib
import sqlite3
router = APIRouter(prefix="/documents", tags=["documents"])

os.makedirs(PDF_STORAGE_PATH, exist_ok=True)


def index_in_background(doc_id, save_path, filename):
    """
    Runs in a background thread after the upload response is already sent.
    Does the slow work: extract text, chunk, embed, store in Chroma.
    Updates SQLite status from 'processing' to 'ready' when done.
    """
    try:
        text = load_single_pdf(save_path)
        if not text.strip():
            conn = get_connection()
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            conn.close()
            return

        parent_chunks = create_parent_chunks(text, PARENT_CHUNK_SIZE, CHUNK_OVERLAP)
        child_chunks, parent_mapping = create_child_chunks(parent_chunks, CHILD_CHUNK_SIZE, CHUNK_OVERLAP)
        embeddings = create_embeddings(child_chunks)
        vector_store.add_chunks(doc_id, child_chunks, parent_chunks, parent_mapping, embeddings)

        conn = get_connection()
        conn.execute("UPDATE documents SET status = 'ready' WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Indexing failed for {doc_id}: {e}")


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    if count >= MAX_PDFS:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Maximum of {MAX_PDFS} PDFs already uploaded.")

    file_bytes = file.file.read()
    if not file_bytes:
        conn.close()
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    content_hash = hashlib.sha256(file_bytes).hexdigest()

    existing = conn.execute(
        "SELECT id, filename FROM documents WHERE content_hash = ?",
        (content_hash,),
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(
            status_code=409,
            detail=f"This PDF is already added: {existing['filename']}",
        )

    doc_id = str(uuid.uuid4())
    save_path = os.path.join(PDF_STORAGE_PATH, f"{doc_id}.pdf")
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    uploaded_at = datetime.now(timezone.utc).isoformat()

    # Save record immediately with status='processing'
    try:
        conn.execute(
            "INSERT INTO documents (id, filename, uploaded_at, status, content_hash) VALUES (?, ?, ?, ?, ?)",
            (doc_id, file.filename, uploaded_at, "processing", content_hash),
        )
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="This PDF is already added.")

    conn.commit()
    conn.close()

    # Start indexing in background — response returns before this finishes
    Thread(target=index_in_background, args=(doc_id, save_path, file.filename), daemon=True).start()

    return DocumentOut(id=doc_id, filename=file.filename, uploaded_at=uploaded_at, status="processing")


@router.get("", response_model=list[DocumentOut])
def list_documents():
    conn = get_connection()
    rows = conn.execute("SELECT id, filename, uploaded_at, status FROM documents").fetchall()
    conn.close()
    return [DocumentOut(id=r["id"], filename=r["filename"], uploaded_at=r["uploaded_at"], status=r["status"]) for r in rows]


def _rename_document_impl(doc_id: str, body: DocumentRenameRequest) -> DocumentOut:
    # Accept both {filename: "..."} and {name: "..."}
    new_name = (body.filename or body.name or "").strip()

    if not new_name:
        raise HTTPException(status_code=422, detail="filename is required.")

    if len(new_name) > 255:
        raise HTTPException(status_code=422, detail="filename is too long (max 255 chars).")

    if "/" in new_name or "\\" in new_name or "\x00" in new_name:
        raise HTTPException(status_code=422, detail="filename contains invalid characters.")

    # Keep naming consistent for PDFs in UI.
    if not new_name.lower().endswith(".pdf"):
        new_name = f"{new_name}.pdf"

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, filename, uploaded_at, status FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Document not found.")

        conn.execute("UPDATE documents SET filename = ? WHERE id = ?", (new_name, doc_id))
        conn.commit()

        updated = conn.execute(
            "SELECT id, filename, uploaded_at, status FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()

        return DocumentOut(
            id=updated["id"],
            filename=updated["filename"],
            uploaded_at=updated["uploaded_at"],
            status=updated["status"],
        )
    finally:
        conn.close()


@router.patch("/{doc_id}", response_model=DocumentOut)
def rename_document(doc_id: str, body: DocumentRenameRequest):
    return _rename_document_impl(doc_id, body)


@router.put("/{doc_id}", response_model=DocumentOut)
def rename_document_put(doc_id: str, body: DocumentRenameRequest):
    return _rename_document_impl(doc_id, body)


# Optional compatibility aliases for clients that call /rename
@router.patch("/{doc_id}/rename", response_model=DocumentOut)
def rename_document_alias(doc_id: str, body: DocumentRenameRequest):
    return _rename_document_impl(doc_id, body)


@router.put("/{doc_id}/rename", response_model=DocumentOut)
def rename_document_alias_put(doc_id: str, body: DocumentRenameRequest):
    return _rename_document_impl(doc_id, body)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str):
    conn = get_connection()
    row = conn.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found.")

    vector_store.delete_document(doc_id)

    file_path = os.path.join(PDF_STORAGE_PATH, f"{doc_id}.pdf")
    if os.path.exists(file_path):
        os.remove(file_path)

    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()