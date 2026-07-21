"""Similarity retrieval over the local ChromaDB index.

Queries the persisted ``legal_clauses`` collection built by
``rag.index_builder`` and returns the most relevant chunks together
with their metadata. Prompt generation and LLM calls are
intentionally not part of this module.
"""

from pathlib import Path
from typing import TypedDict

import chromadb

from rag.config import COLLECTION_NAME, VECTOR_STORE_DIR
from rag.embeddings import embed_texts

DEFAULT_TOP_K = 3


class RetrievedChunk(TypedDict):
    """A single retrieved chunk with its metadata and distance."""

    id: str
    filename: str
    chunk_index: int
    text: str
    distance: float


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    persist_dir: Path = VECTOR_STORE_DIR,
) -> list[RetrievedChunk]:
    """Return the ``top_k`` most relevant chunks for ``query``.

    Args:
        query: Natural-language query string.
        top_k: Maximum number of chunks to return.
        persist_dir: Directory where ChromaDB persists the collection.

    Returns:
        A list of chunks ordered by relevance (lowest distance
        first), each with ``id``, ``filename``, ``chunk_index``,
        ``text``, and ``distance``. Returns an empty list when the
        collection is empty.

    Raises:
        ValueError: If ``query`` is blank or ``top_k`` is not
            positive.
        FileNotFoundError: If no index exists at ``persist_dir``.
    """
    if not query.strip():
        raise ValueError("query must not be empty.")
    if top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    if not persist_dir.exists():
        raise FileNotFoundError(
            f"Vector store not found at '{persist_dir}'. "
            "Run 'python -m rag.index_builder' first."
        )

    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    count = collection.count()
    if count == 0:
        return []

    query_embedding = embed_texts([query])
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    for chunk_id, document, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            {
                "id": chunk_id,
                "filename": metadata["filename"],
                "chunk_index": metadata["chunk_index"],
                "text": document,
                "distance": distance,
            }
        )

    return chunks
