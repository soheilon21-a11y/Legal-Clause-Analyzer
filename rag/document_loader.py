"""Document loading for the knowledge base.

Reads reference legal documents from the knowledge base directory and
returns their raw text together with filename metadata. This is the
first step of the RAG indexing pipeline; its output feeds
``rag.text_chunker``.
"""

from pathlib import Path
from typing import TypedDict

from rag.config import KNOWLEDGE_BASE_DIR


class Document(TypedDict):
    """A single loaded knowledge-base document."""

    filename: str
    text: str


def load_documents(directory: Path = KNOWLEDGE_BASE_DIR) -> list[Document]:
    """Load every non-empty ``.txt`` file from ``directory``.

    Args:
        directory: Knowledge-base directory to scan. Defaults to the
            configured ``KNOWLEDGE_BASE_DIR``.

    Returns:
        A list of documents in deterministic (filename-sorted) order,
        each with ``filename`` and ``text``.

    Raises:
        FileNotFoundError: If ``directory`` does not exist.
        NotADirectoryError: If ``directory`` exists but is not a
            directory.
    """
    if not directory.exists():
        raise FileNotFoundError(
            f"Knowledge base directory does not exist: {directory}"
        )
    if not directory.is_dir():
        raise NotADirectoryError(
            f"Knowledge base path is not a directory: {directory}"
        )

    documents: list[Document] = []
    for path in sorted(directory.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        documents.append({"filename": path.name, "text": text})

    return documents
