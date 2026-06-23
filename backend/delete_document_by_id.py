"""
Delete a specific document by ID (including Chroma vectors and disk file).
Use when you've identified a duplicate that needs to be removed.
Run from backend folder: python delete_document_by_id.py <doc_id>
"""
import sys
import os
from app.database import get_connection
from app.config import PDF_STORAGE_PATH
from app.rag import vector_store

def delete_by_id(doc_id):
    """Delete a document completely by its ID."""
    conn = get_connection()
    
    # Get document info
    row = conn.execute(
        "SELECT id, filename FROM documents WHERE id = ?",
        (doc_id,)
    ).fetchone()
    
    if not row:
        print(f"✗ Document not found: {doc_id}")
        conn.close()
        return False
    
    filename = row[1]
    print(f"Deleting: {filename} (id: {doc_id})")
    
    # Step 1: Delete from Chroma vector store
    print("  1. Removing from vector store...")
    try:
        vector_store.delete_document(doc_id)
        print("     ✓ Vector store cleaned")
    except Exception as e:
        print(f"     ⚠ Vector store error: {e}")
    
    # Step 2: Delete PDF file from disk
    print("  2. Removing PDF file from disk...")
    file_path = os.path.join(PDF_STORAGE_PATH, f"{doc_id}.pdf")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print("     ✓ PDF file deleted")
        except Exception as e:
            print(f"     ✗ Failed to delete file: {e}")
            conn.close()
            return False
    else:
        print(f"     ⚠ PDF file not found at {file_path}")
    
    # Step 3: Delete from SQLite
    print("  3. Removing database record...")
    try:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        print("     ✓ Database record deleted")
    except Exception as e:
        print(f"     ✗ Database error: {e}")
        conn.close()
        return False
    
    conn.close()
    print(f"\n✓ Successfully deleted: {filename}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python delete_document_by_id.py <doc_id>")
        print("Example: python delete_document_by_id.py 7eba02d0-f594-4ac6-a617-68b296d8dd24")
        sys.exit(1)
    
    doc_id = sys.argv[1].strip()
    if not delete_by_id(doc_id):
        sys.exit(1)
