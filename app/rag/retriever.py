from __future__ import annotations

import chromadb

from app.core.config import get_embedder, settings

_chroma: chromadb.ClientAPI | None = None


def _chroma_client() -> chromadb.ClientAPI:
    global _chroma
    if _chroma is None:
        _chroma = chromadb.PersistentClient(path=settings.chroma_db_path)  # type: ignore[assignment]
    return _chroma  # type: ignore[return-value]


def search(collection_name: str, query: str, n_results: int = 5) -> list[str]:
    client = _chroma_client()
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return []

    embedding = get_embedder().embed_query(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
    )
    docs: list[list[str]] = results.get("documents", [[]])
    return docs[0] if docs else []


def search_joined(collection_name: str, query: str, n_results: int = 5) -> str:
    docs = search(collection_name, query, n_results)
    return "\n\n".join(docs)
