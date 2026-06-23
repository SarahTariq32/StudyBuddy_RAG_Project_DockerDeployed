"""
Backfill content_hash for all existing documents in the database.
This ensures older PDFs (uploaded before the duplicate check feature) are also protected.
Run once from backend folder: python backfill_content_hash.py
"""
import os
import hashlib
from app.database import get_connection
from app.config import PDF_STORAGE_PATH

def backfill_hashes():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all documents with NULL content_hash
    rows = cursor.execute(
        "SELECT id, filename FROM documents WHERE content_hash IS NULL"
    ).fetchall()
    
    if not rows:
        print("✓ All documents already have content_hash. Nothing to backfill.")
        conn.close()
        return
    
    print(f"Backfilling {len(rows)} documents...\n")
    
    duplicates_found = []
    updated = 0
    
    for doc_id, filename in rows:
        pdf_path = os.path.join(PDF_STORAGE_PATH, f"{doc_id}.pdf")
        
        if not os.path.exists(pdf_path):
            print(f"⚠ {filename}: PDF file not found at {pdf_path}")
            continue
        
        # Read and hash the PDF
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()
            content_hash = hashlib.sha256(file_bytes).hexdigest()
        
        # Check if this hash already exists (indicates a duplicate)
        existing = cursor.execute(
            "SELECT id, filename FROM documents WHERE content_hash = ?",
            (content_hash,)
        ).fetchone()
        
        if existing and existing[0] != doc_id:
            duplicates_found.append({
                'current': (doc_id, filename),
                'existing': existing,
                'hash': content_hash
            })
            print(f"⚠ DUPLICATE DETECTED:")
            print(f"   Existing: {existing[1]} (id: {existing[0]})")
            print(f"   Current:  {filename} (id: {doc_id})")
            print(f"   Hash: {content_hash}\n")
            continue
        
        # Update the document with content_hash
        try:
            cursor.execute(
                "UPDATE documents SET content_hash = ? WHERE id = ?",
                (content_hash, doc_id)
            )
            updated += 1
            print(f"✓ {filename}")
        except Exception as e:
            print(f"✗ {filename}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n--- Summary ---")
    print(f"Updated: {updated} documents")
    print(f"Duplicates found: {len(duplicates_found)}")
    
    if duplicates_found:
        print(f"\nDuplicate PDFs to delete (keep only the first one):")
        for dup in duplicates_found:
            print(f"  - {dup['current'][1]} (id: {dup['current'][0]}) - DUPLICATE")
            print(f"    Keep: {dup['existing'][1]} (id: {dup['existing'][0]})")

if __name__ == "__main__":
    print("Starting content_hash backfill...\n")
    backfill_hashes()
    print("\nDone!")
