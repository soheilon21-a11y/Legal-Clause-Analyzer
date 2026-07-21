"""Embedding model access for the RAG pipeline.

Wraps a local sentence-transformers model and exposes a minimal
function to embed texts for indexing. The model is loaded lazily and
cached for the lifetime of the process.
"""

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Return the embedding model, downloading it on first use."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate one embedding vector per input text.

    Args:
        texts: Raw text chunks to embed.

    Returns:
        A list of embedding vectors, one per input text, in the same
        order. An empty input yields an empty list.
    """
    if not texts:
        return []

    embeddings = get_embedding_model().encode(texts)
    return [vector.tolist() for vector in embeddings]
