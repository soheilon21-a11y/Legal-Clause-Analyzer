"""
Retrieval-Augmented Generation (RAG) package.

Provides a fully local RAG pipeline for grounding LLM summaries in
curated legal reference documents. Includes document loading from
plain-text files, overlapping character-based chunking, embedding
generation via sentence-transformers (BAAI/bge-small-en-v1.5),
persistent ChromaDB indexing, and Top-K similarity retrieval.
"""  