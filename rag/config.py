"""Configuration placeholders for the RAG pipeline.

Centralizes paths, the vector-store collection name, and chunking
parameters so later phases have a single place to tune them.
No runtime logic lives here.
"""

from pathlib import Path

# Locations
KNOWLEDGE_BASE_DIR = Path("knowledge_base")
VECTOR_STORE_DIR = Path("vector_store")

# Vector store
COLLECTION_NAME = "legal_clauses"

# Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
