import chromadb
import os
import shutil
from app.config import (
    CHROMA_PATH,
    CHROMA_HOST,
    CHROMA_PORT,
    CHROMA_COLLECTION,
    MAX_PARENT_TEXT_IN_METADATA,
)

# One persistent ChromaDB client for the whole app lifetime.
# "persistent" means the collection is saved to disk at CHROMA_PATH
# and survives restarts — unlike an in-memory client which resets every run.
if CHROMA_HOST:
    # Docker/service mode: use external Chroma service (e.g. compose service "db").
    _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    print(f"[INFO] ChromaDB client connected via HTTP at {CHROMA_HOST}:{CHROMA_PORT}")
else:
    # Standalone mode: use local persistent path.
    _client = chromadb.PersistentClient(path=CHROMA_PATH)
    print(f"[INFO] ChromaDB client using local path: {CHROMA_PATH}")

def _create_collection_with_recovery():
    """
    Recover from known local Chroma config shape mismatches (for example
    KeyError: '_type' while reading old collection metadata) by resetting
    the local persisted directory. This only applies to standalone mode.
    """
    global _client
    try:
        return _client.get_or_create_collection(name=CHROMA_COLLECTION)
    except Exception as exc:
        is_local_mode = not CHROMA_HOST
        msg = str(exc)
        if not is_local_mode:
            raise
        if "_type" not in msg:
            raise

        print("[INFO] Chroma local metadata is incompatible. Resetting local Chroma store...")
        try:
            if os.path.exists(CHROMA_PATH):
                shutil.rmtree(CHROMA_PATH, ignore_errors=True)
            os.makedirs(CHROMA_PATH, exist_ok=True)

            # Chroma caches client systems per path/process. Clear cache so a
            # fresh PersistentClient is actually created after reset.
            try:
                from chromadb.api.client import SharedSystemClient  # type: ignore

                SharedSystemClient.clear_system_cache()
            except Exception:
                pass

            _client = chromadb.PersistentClient(path=CHROMA_PATH)
            print(f"[INFO] ChromaDB store reset at: {CHROMA_PATH}")
            return _client.get_or_create_collection(name=CHROMA_COLLECTION)
        except Exception as retry_exc:
            print(f"[ERROR] Chroma recovery failed: {retry_exc}")
            print("[WARN] Falling back to in-memory Chroma client for this session.")
            try:
                _client = chromadb.EphemeralClient()
                return _client.get_or_create_collection(name=CHROMA_COLLECTION)
            except Exception:
                raise


_collection = _create_collection_with_recovery()


def add_chunks(
    doc_id: str,
    source: str,
    child_chunks: list[str],
    parent_chunks: list[str],
    parent_mapping: list[int],
    embeddings: list[list[float]],
) -> None:
    """
    Store child chunks in ChromaDB.

    Each child chunk gets:
      - its own embedding vector (used for similarity search)
      - metadata containing:
          doc_id      — which PDF this chunk came from (needed for deletion)
          source      — original filename (used for source attribution in answers)
          parent_text — the full parent chunk text (returned at retrieval time
                        so the answer is grounded in a larger context window)

    The ID for each chunk is "{doc_id}_{index}" — must be unique across the collection.
    """
    ids = [f"{doc_id}_{i}" for i in range(len(child_chunks))]
    metadatas = [
        {
            "doc_id": doc_id,
            "source": source,
            "parent_text": parent_chunks[parent_mapping[i]][:MAX_PARENT_TEXT_IN_METADATA],
        }
        for i in range(len(child_chunks))
    ]

    _collection.add(
        ids=ids,
        documents=child_chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search(query_embedding: list[float], top_k: int) -> list[dict]:
    """
    Find the top_k child chunks closest to the query embedding.
    Returns a list of dicts with metadata and distance score.
    """
    if _collection.count() == 0:
        return []

    count = _collection.count()
    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, count),
        include=["metadatas", "distances"],
    )

    metadatas = results.get("metadatas")
    distances = results.get("distances")
    if not metadatas or not metadatas[0]:
        return []

    scored_hits: list[dict] = []
    row_distances = distances[0] if distances and distances[0] else []
    for i, metadata in enumerate(metadatas[0]):
        hit = dict(metadata or {})
        if not hit.get("parent_text"):
            print(f"WARNING: Missing parent_text metadata in search hit index={i}")
        hit["distance"] = row_distances[i] if i < len(row_distances) else 1e9
        # Gracefully handle chunks indexed before 'source' was added to metadata.
        if not hit.get("source"):
            hit["source"] = hit.get("doc_id", "unknown")
        scored_hits.append(hit)

    return scored_hits


def delete_document(doc_id: str) -> None:
    """
    Delete every chunk that belongs to doc_id.
    ChromaDB's where filter matches on metadata fields —
    this removes all chunks whose metadata["doc_id"] == doc_id.
    """
    _collection.delete(where={"doc_id": doc_id})
