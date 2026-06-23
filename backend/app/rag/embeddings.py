from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

# Load once at module import time — avoids reloading the model on every call.
# The first run downloads the model weights; subsequent runs load from cache.
_model = SentenceTransformer(EMBEDDING_MODEL)


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Encode a list of strings into normalized embedding vectors.
    Returns a list of float lists (one per input text).
    """
    embeddings = _model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
    )
    return embeddings.tolist()
