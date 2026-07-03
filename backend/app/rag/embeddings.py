from app.config import EMBEDDING_BATCH_SIZE
import importlib
import time


def _build_embedder():
    """
    Lazy-load Chroma embedder to avoid IDE false missing-import warnings.
    """
    try:
        mod = importlib.import_module("chromadb.utils.embedding_functions")
        return mod.DefaultEmbeddingFunction()
    except Exception as exc:
        raise RuntimeError(
            "chromadb is not available in the active interpreter. "
            "Select backend\\.venv interpreter in VS Code."
        ) from exc


_embedder = _build_embedder()


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Encode a list of strings into embedding vectors.
    Preserves input order and returns one vector per input text.
    """
    if not texts:
        return []

    # Keep length/order stable: replace empty/blank text with a single space.
    normalized = [(t if (t or "").strip() else " ") for t in texts]

    batch_size = EMBEDDING_BATCH_SIZE if EMBEDDING_BATCH_SIZE > 0 else 48
    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(normalized), batch_size):
        batch = normalized[batch_start : batch_start + batch_size]
        last_exc = None

        for attempt in range(3):
            try:
                raw_vectors = _embedder(batch)
                vectors = [[float(x) for x in vec] for vec in raw_vectors]
                all_embeddings.extend(vectors)
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(1.5)
        else:
            raise RuntimeError(
                f"Embedding generation failed after retries on batch "
                f"{batch_start}–{batch_start + len(batch)}: {last_exc}"
            ) from last_exc

    return all_embeddings
