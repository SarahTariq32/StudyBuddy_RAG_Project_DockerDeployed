"""
Peek inside the ChromaDB collection to confirm chunks were stored correctly.
Run this after uploading a PDF via Postman.
"""
import chromadb
from app.config import CHROMA_PATH

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name="documents")

total = collection.count()
print(f"Total chunks in collection: {total}")

if total > 0:
    # Fetch the first 3 chunks to inspect
    sample = collection.get(limit=3, include=["documents", "metadatas"])
    for i, (doc, meta) in enumerate(zip(sample["documents"], sample["metadatas"])):
        print(f"\n--- Chunk {i} ---")
        print(f"  doc_id      : {meta['doc_id']}")
        print(f"  child text  : {doc[:80]}...")
        print(f"  parent_text : {meta['parent_text'][:80]}...")
