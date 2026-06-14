"""
RAG 소스 파일(PDF 2종, Excel 1종)을 ChromaDB에 인덱싱.
실행: uv run python app/rag/ingest.py
"""
from __future__ import annotations

import time

import chromadb
import fitz  # PyMuPDF
import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_embedder, settings

_RETRY_WAIT = 60  # 429 발생 시 대기 시간(초)


def _embed_with_retry(texts: list[str]) -> list[list[float]]:
    for attempt in range(3):
        try:
            return get_embedder().embed_documents(texts)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                print(f"\n  rate limit 감지, {_RETRY_WAIT}초 대기 후 재시도...")
                time.sleep(_RETRY_WAIT)
            else:
                raise
    raise RuntimeError("embed 재시도 횟수 초과")


def _reset_collection(
    chroma: chromadb.ClientAPI, name: str
) -> chromadb.Collection:
    try:
        chroma.delete_collection(name)
    except Exception:
        pass
    return chroma.create_collection(name)


def ingest_pdf(
    pdf_path: str,
    collection_name: str,
    chroma: chromadb.ClientAPI,
) -> int:
    doc = fitz.open(pdf_path)
    full_text = "".join(page.get_text() for page in doc)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(full_text)

    collection = _reset_collection(chroma, collection_name)

    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings = _embed_with_retry(batch)
        ids = [f"{collection_name}_{i + j}" for j in range(len(batch))]
        collection.add(ids=ids, embeddings=embeddings, documents=batch)
        time.sleep(0.7)

    return len(chunks)


def ingest_excel(
    excel_path: str,
    collection_name: str,
    chroma: chromadb.ClientAPI,
) -> int:
    df = pd.read_excel(excel_path)

    def row_to_text(row: pd.Series) -> str:
        parts = [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
        return ", ".join(parts)

    texts = [row_to_text(row) for _, row in df.iterrows()]
    collection = _reset_collection(chroma, collection_name)

    batch_size = 100
    total = len(texts)
    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        embeddings = _embed_with_retry(batch)
        ids = [f"{collection_name}_{i + j}" for j in range(len(batch))]
        collection.add(ids=ids, embeddings=embeddings, documents=batch)
        print(f"  [{collection_name}] {min(i + batch_size, total)}/{total}", end="\r")
        time.sleep(0.7)

    return total


def run() -> None:
    chroma = chromadb.PersistentClient(path=settings.chroma_db_path)
    t0 = time.time()

    count = ingest_pdf(settings.policy_pdf_path, "policy", chroma)
    print(f"[policy]     {count:>6} chunks")

    count = ingest_pdf(settings.guidelines_pdf_path, "guidelines", chroma)
    print(f"[guidelines] {count:>6} chunks")

    count = ingest_excel(settings.food_db_excel_path, "food_db", chroma)
    print(f"[food_db]    {count:>6} rows")

    print(f"완료 ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    run()
