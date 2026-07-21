"""Text chunking utilities.

Splits loaded documents into overlapping chunks using the sizes from
``rag.config`` while preserving filename metadata. Its output is the
input for the future embedding and vector-store phase.
"""

from typing import TypedDict

from rag.config import CHUNK_OVERLAP, CHUNK_SIZE
from rag.document_loader import Document


class Chunk(TypedDict):
    """A single text chunk with its source metadata."""

    filename: str
    chunk_index: int
    text: str


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split ``text`` into overlapping character-based chunks.

    Args:
        text: The text to split.
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of characters shared between consecutive
            chunks. Must be smaller than ``chunk_size``.

    Returns:
        A list of chunk strings in order. Empty text yields an empty
        list; text shorter than ``chunk_size`` yields a single chunk.

    Raises:
        ValueError: If the chunking parameters are invalid.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be zero or positive.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap

    return chunks


def chunk_documents(documents: list[Document]) -> list[Chunk]:
    """Split every document into chunks, preserving filename metadata.

    Args:
        documents: Documents as returned by
            ``rag.document_loader.load_documents``.

    Returns:
        A flat list of chunks in document order, each carrying
        ``filename``, ``chunk_index``, and ``text``.
    """
    chunks: list[Chunk] = []
    for document in documents:
        for index, text in enumerate(chunk_text(document["text"])):
            chunks.append(
                {
                    "filename": document["filename"],
                    "chunk_index": index,
                    "text": text,
                }
            )

    return chunks
