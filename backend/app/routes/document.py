import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.config import MAX_PDFS, PDF_STORAGE_PATH, PARENT_CHUNK_SIZE, CHILD_CHUNK_SIZE, CHUNK_OVERLAP
from app.database import get_connection
from app.schemas import DocumentOut
from app.rag.loader import load_single_pdf
from app.rag.chunking import create_parent_chunks, create_child_chunks
from app.rag.embeddings import create_embeddings
from app.rag import vector_store

router = APIRouter(prefix="/documents", tags=["documents"])

# Make sure the storage folder exists before anyone tries to save into it.
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile = File(...)):
    """
    Accept a PDF upload, run the full indexing pipeline, and store the record.
    Steps (all synchronous):
      1. Enforce the MAX_PDFS cap
      2. Save the raw file to disk
      3. Extract text → parent chunks → child chunks → embeddings
      4. Store chunks in ChromaDB
      5. Record the document in SQLite
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    conn = get_connection()

    # --- Enforce cap ---
    count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    if count >= MAX_PDFS:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_PDFS} PDFs already uploaded. Delete one first.",
        )

    # --- Save file to disk ---
    doc_id = str(uuid.uuid4())
    save_path = os.path.join(PDF_STORAGE_PATH, f"{doc_id}.pdf")
    with open(save_path, "wb") as f:
        f.write(file.file.read())

    # --- Indexing pipeline ---
    text = load_single_pdf(save_path)
    parent_chunks = create_parent_chunks(text, PARENT_CHUNK_SIZE, CHUNK_OVERLAP)
    child_chunks, parent_mapping = create_child_chunks(parent_chunks, CHILD_CHUNK_SIZE, CHUNK_OVERLAP)
    embeddings = create_embeddings(child_chunks)
    vector_store.add_chunks(doc_id, child_chunks, parent_chunks, parent_mapping, embeddings)

    # --- Save record to SQLite ---
    uploaded_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO documents (id, filename, uploaded_at) VALUES (?, ?, ?)",
        (doc_id, file.filename, uploaded_at),
    )
    conn.commit()
    conn.close()

    return DocumentOut(id=doc_id, filename=file.filename, uploaded_at=uploaded_at)


@router.get("", response_model=list[DocumentOut])
def list_documents():
    """
    Return all documents recorded in SQLite.
    SQLite is the source of truth for document records — Chroma stores chunks,
    not document-level metadata like filename and upload time.
    """
    conn = get_connection()
    rows = conn.execute("SELECT id, filename, uploaded_at FROM documents").fetchall()
    conn.close()
    return [DocumentOut(id=row["id"], filename=row["filename"], uploaded_at=row["uploaded_at"]) for row in rows]


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str):
    """
    Remove a document completely. Three cleanup steps are required — skipping
    any one of them leaves the app in a broken or leaky state:

      1. ChromaDB  — delete all chunks with this doc_id from the vector index.
                     If skipped: searches will still return this document's text
                     forever, even after the PDF is "deleted".

      2. Disk      — delete the raw PDF file from storage/pdfs/.
                     If skipped: the file accumulates on disk indefinitely,
                     and the storage cap becomes meaningless.

      3. SQLite    — remove the document row from the documents table.
                     If skipped: GET /documents still lists the document as
                     existing, and the MAX_PDFS cap still counts it.
    """
    conn = get_connection()
    row = conn.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found.")

    # Step 1: Remove all chunks from the vector store.
    # where={"doc_id": doc_id} is a metadata filter — Chroma scans every stored
    # chunk's metadata and deletes any whose doc_id field matches exactly.
    vector_store.delete_document(doc_id)

    # Step 2: Delete the file from disk.
    file_path = os.path.join(PDF_STORAGE_PATH, f"{doc_id}.pdf")
    if os.path.exists(file_path):
        os.remove(file_path)

    # Step 3: Remove the record from SQLite.
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
