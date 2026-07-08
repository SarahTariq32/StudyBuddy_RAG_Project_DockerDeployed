from app.config import TOP_K, NUM_MULTI_QUERIES, MAX_CONTEXT_PARENTS, DISTANCE_THRESHOLD
from app.rag.embeddings import create_embeddings
from app.rag.query_rewrite import generate_multi_queries
from app.rag import vector_store


def _ranked_parent_hits(queries: list[str], seen: set[str]) -> tuple[list[dict], list[dict]]:
    """
    Embed each query, search Chroma, filter by distance threshold, and rank
    candidates by vector distance (lower is better).
    Returns new unique parent texts only (not already in `seen`), each as a
    dict with keys: text (str), source (str).
    """
    if not queries:
        return [], []

    scored: list[tuple[float, str, str]] = []
    debug_hits: list[dict] = []
    for embedding in create_embeddings(queries):
        hits = vector_store.search(embedding, TOP_K)
        for hit in hits:
            parent_text = hit.get("parent_text", "")
            source = hit.get("source", "")
            distance = float(hit.get("distance", 1e9))
            debug_hits.append(
                {
                    "source": source,
                    "distance": distance,
                    "parent_preview": parent_text[:240],
                }
            )
            # Skip chunks that are too dissimilar to be useful context.
            if not parent_text or parent_text in seen:
                continue
            if distance > DISTANCE_THRESHOLD:
                continue
            scored.append((distance, parent_text, source))

    scored.sort(key=lambda x: x[0])

    ordered_unique: list[dict] = []
    local_seen: set[str] = set()
    for _, parent_text, source in scored:
        if parent_text in local_seen:
            continue
        local_seen.add(parent_text)
        ordered_unique.append({"text": parent_text, "source": source})
    return ordered_unique, debug_hits


def retrieve_context(question: str) -> list[dict]:
    """
    Multi-query retrieval: rewrite the question, search Chroma for each variant,
    dedupe parent chunks, and return up to MAX_CONTEXT_PARENTS unique parents.
    Each entry is a dict with keys: text (str), source (str).
    """
    return retrieve_context_with_debug(question).get("context", [])


def retrieve_context_with_debug(question: str) -> dict:
    """
    Same retrieval behavior as retrieve_context, but returns debug artifacts used
    for observability and dashboard views.
    """
    question = (question or "").strip()
    if not question:
        return {
            "context": [],
            "rewrites": [],
            "retrieval_hits": [],
            "multi_query_used": False,
        }

    seen: set[str] = set()
    parents: list[dict] = []
    retrieval_hits: list[dict] = []

    # First pass: direct retrieval from the original question only.
    primary, first_hits = _ranked_parent_hits([question], seen)
    retrieval_hits.extend(first_hits)
    for item in primary:
        seen.add(item["text"])
        parents.append(item)
        if len(parents) >= MAX_CONTEXT_PARENTS:
            # Generate rewrites for UI visibility even though we already have enough context
            rewrites = []
            if NUM_MULTI_QUERIES > 0:
                try:
                    rewrites = [q for q in generate_multi_queries(question, NUM_MULTI_QUERIES) if q]
                except Exception as exc:
                    print(f"Query rewrite failed (early exit): {exc}")
            return {
                "context": parents,
                "rewrites": rewrites,
                "retrieval_hits": retrieval_hits,
                "multi_query_used": bool(rewrites),
            }

    # Fast path: if direct retrieval already found enough context, skip
    # LLM-based query rewriting to reduce latency.
    enough_without_rewrite = min(3, MAX_CONTEXT_PARENTS)
    if len(parents) >= enough_without_rewrite or NUM_MULTI_QUERIES <= 0:
        return {
            "context": parents,
            "rewrites": [],
            "retrieval_hits": retrieval_hits,
            "multi_query_used": False,
        }

    # Second pass: broaden recall using rewritten variants; tolerate rewrite
    # failures so /ask still works with direct retrieval.
    try:
        rewrites = [q for q in generate_multi_queries(question, NUM_MULTI_QUERIES) if q]
    except Exception as exc:
        print(f"Query rewrite failed; falling back to direct retrieval: {exc}")
        rewrites = []

    expanded, expanded_hits = _ranked_parent_hits(rewrites, seen)
    retrieval_hits.extend(expanded_hits)
    for item in expanded:
        seen.add(item["text"])
        parents.append(item)
        if len(parents) >= MAX_CONTEXT_PARENTS:
            break

    return {
        "context": parents,
        "rewrites": rewrites,
        "retrieval_hits": retrieval_hits,
        "multi_query_used": bool(rewrites),
    }
