from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from app.config import EMBEDDING_BATCH_SIZE
import time

# Uses Chroma's ONNX-based default embedding model (CPU-friendly and lighter
# than installing full PyTorch + sentence-transformers in container builds).
_embedder = DefaultEmbeddingFunction()


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Encode a list of strings into normalized embedding vectors.
    Processes texts in batches of EMBEDDING_BATCH_SIZE to avoid memory
    exhaustion on large indexing jobs.
    Returns a list of float lists (one per input text), preserving order.
    """
    cleaned = [text for text in texts if (text or "").strip()]
    if not cleaned:
        raise ValueError("No non-empty text provided for embeddings")

    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(cleaned), EMBEDDING_BATCH_SIZE):
        batch = cleaned[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
        last_exc = None
        for attempt in range(3):
            try:
                batch_embeddings = _embedder(batch)
                all_embeddings.extend(batch_embeddings)
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
