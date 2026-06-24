import chromadb
from app.config import CHROMA_PATH, MAX_PARENT_TEXT_IN_METADATA

# One persistent ChromaDB client for the whole app lifetime.
# "persistent" means the collection is saved to disk at CHROMA_PATH
# and survives restarts — unlike an in-memory client which resets every run.
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection(name="documents")


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
