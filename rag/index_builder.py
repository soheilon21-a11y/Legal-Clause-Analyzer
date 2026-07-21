"""Offline index builder for the RAG knowledge base.

Pipeline: load documents, chunk them, embed the chunks, and store
them in a local ChromaDB collection. Retrieval is intentionally not
part of this module.

Run directly from the project root to (re)build the index:

    python -m rag.index_builder
"""

from pathlib import Path

import chromadb

from rag.config import (
    COLLECTION_NAME,
    KNOWLEDGE_BASE_DIR,
    VECTOR_STORE_DIR,
)
from rag.document_loader import load_documents
from rag.embeddings import embed_texts
from rag.text_chunker import Chunk, chunk_documents


def _chunk_id(chunk: Chunk) -> str:
    """Return a deterministic ID for a chunk."""
    return f"{chunk['filename']}:{chunk['chunk_index']}"


def build_index(
    knowledge_base_dir: Path = KNOWLEDGE_BASE_DIR,
    persist_dir: Path = VECTOR_STORE_DIR,
) -> int:
    """Build the local ChromaDB index from the knowledge base.

    Chunks are upserted under deterministic IDs, so re-running the
    builder refreshes the collection without duplicating entries.

    Args:
        knowledge_base_dir: Directory of ``.txt`` documents to index.
        persist_dir: Directory where ChromaDB persists the collection.

    Returns:
        The number of chunks stored in the collection.
    """
    documents = load_documents(knowledge_base_dir)
    chunks = chunk_documents(documents)

    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    if chunks:
        collection.upsert(
            ids=[_chunk_id(chunk) for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[
                {
                    "filename": chunk["filename"],
                    "chunk_index": chunk["chunk_index"],
                }
                for chunk in chunks
            ],
            embeddings=embed_texts(
                [chunk["text"] for chunk in chunks]
            ),
        )

    print(
        "Indexing complete: "
        f"{len(documents)} document(s), "
        f"{len(chunks)} chunk(s) stored in collection "
        f"'{COLLECTION_NAME}' at '{persist_dir}'."
    )
    return len(chunks)


if __name__ == "__main__":
    build_index()
