from __future__ import annotations

import threading

import chromadb
from rank_bm25 import BM25Okapi

from app.core.config import get_embedder, settings

# ── 싱글톤 ────────────────────────────────────────────────────────────────────

_chroma: chromadb.ClientAPI | None = None
_chroma_lock = threading.Lock()
_bm25: BM25Okapi | None = None
_bm25_ids: list[str] = []
_bm25_lock = threading.Lock()


def _chroma_client() -> chromadb.ClientAPI:
    global _chroma
    if _chroma is None:
        with _chroma_lock:
            if _chroma is None:
                _chroma = chromadb.PersistentClient(path=settings.chroma_db_path)  # type: ignore[assignment]
    return _chroma  # type: ignore[return-value]


def _tok(text: str) -> list[str]:
    """한국어 식품명용 2-gram 캐릭터 토크나이저."""
    t = text.replace(" ", "")
    return [t[i : i + 2] for i in range(len(t) - 1)] or list(t)


def _get_bm25() -> tuple[BM25Okapi, list[str]]:
    global _bm25, _bm25_ids
    if _bm25 is None:
        with _bm25_lock:
            if _bm25 is None:
                result = _chroma_client().get_collection("food_db").get(include=["documents"])
                docs: list[str] = result["documents"]
                _bm25_ids = result["ids"]
                _bm25 = BM25Okapi([_tok(d) for d in docs])
    return _bm25, _bm25_ids


# ── 검색 ──────────────────────────────────────────────────────────────────────

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


def search_food(query: str, n_results: int = 5) -> str:
    """food_db 하이브리드 검색 (BM25 + 벡터) — RRF 병합 후 식품명 + 영양성분 반환."""
    try:
        collection = _chroma_client().get_collection("food_db")
    except Exception:
        return ""

    fetch = n_results * 2

    # 벡터 검색
    embedding = get_embedder().embed_query(query)
    vec = collection.query(
        query_embeddings=[embedding],
        n_results=fetch,
        include=[],
    )
    vec_ids: list[str] = vec["ids"][0]

    # BM25 검색
    bm25, all_ids = _get_bm25()
    scores = bm25.get_scores(_tok(query))
    bm25_ids = [
        all_ids[i]
        for i in sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)[:fetch]
    ]

    # RRF 병합 (k=60)
    rrf: dict[str, float] = {}
    for rank, id_ in enumerate(vec_ids):
        rrf[id_] = rrf.get(id_, 0.0) + 1 / (60 + rank + 1)
    for rank, id_ in enumerate(bm25_ids):
        rrf[id_] = rrf.get(id_, 0.0) + 1 / (60 + rank + 1)

    top_ids = sorted(rrf, key=rrf.__getitem__, reverse=True)[:n_results]

    # 최종 데이터 조회 — id 매핑 후 RRF 순서대로 재구성
    final = collection.get(ids=top_ids, include=["documents", "metadatas"])
    id_map: dict[str, tuple[str, dict]] = {
        id_: (doc, meta)
        for id_, doc, meta in zip(final["ids"], final["documents"], final["metadatas"])
    }
    parts = []
    for id_ in top_ids:
        if id_ not in id_map:
            continue
        name, meta = id_map[id_]
        parts.append(f"{name} — {', '.join(f'{k}: {v}' for k, v in meta.items())}")

    return "\n\n".join(parts)
