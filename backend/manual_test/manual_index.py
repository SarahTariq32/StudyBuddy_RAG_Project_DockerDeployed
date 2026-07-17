"""
Manually index a PDF from storage/pdfs without going through the HTTP route.
This calls the exact same pipeline functions as POST /documents.
Run with: python test_index.py
"""
import uuid
from datetime import datetime, timezone

from app.config import PARENT_CHUNK_SIZE, CHILD_CHUNK_SIZE, CHUNK_OVERLAP
from app.database import get_connection, init_db
from app.rag.loader import load_single_pdf
from app.rag.chunking import create_parent_chunks, create_child_chunks
from app.rag.embeddings import create_embeddings
from app.rag import vector_store

# --- Pick the PDF to index ---
PDF_PATH = r"storage/pdfs/_OceanofPDF.com_The_Alchemist_-_Paulo_conho.pdf"
FILENAME  = "The_Alchemist.pdf"

print("Step 1: Loading PDF text...")
text = load_single_pdf(PDF_PATH)
print(f"  Extracted {len(text)} characters")

print("Step 2: Creating parent chunks...")
parent_chunks = create_parent_chunks(text, PARENT_CHUNK_SIZE, CHUNK_OVERLAP)
print(f"  {len(parent_chunks)} parent chunks")

print("Step 3: Creating child chunks...")
child_chunks, parent_mapping = create_child_chunks(parent_chunks, CHILD_CHUNK_SIZE, CHUNK_OVERLAP)
print(f"  {len(child_chunks)} child chunks")

print("Step 4: Creating embeddings (this takes a moment)...")
embeddings = create_embeddings(child_chunks)
print(f"  {len(embeddings)} embeddings, dim={len(embeddings[0])}")

print("Step 5: Storing in ChromaDB...")
doc_id = str(uuid.uuid4())
vector_store.add_chunks(doc_id, child_chunks, parent_chunks, parent_mapping, embeddings)
print(f"  Stored with doc_id: {doc_id}")

print("Step 6: Saving record to SQLite...")
init_db()
conn = get_connection()
uploaded_at = datetime.now(timezone.utc).isoformat()
conn.execute(
    "INSERT INTO documents (id, filename, uploaded_at) VALUES (?, ?, ?)",
    (doc_id, FILENAME, uploaded_at),
)
conn.commit()
conn.close()

print("\nDone! Now run: python check_chroma.py")
