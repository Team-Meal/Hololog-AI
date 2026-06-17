"""
RAG 소스 파일(PDF 2종, Excel 1종)을 ChromaDB에 인덱싱.
실행: uv run python app/rag/ingest.py
"""
from __future__ import annotations

import time

import chromadb
import fitz  # PyMuPDF
import pandas as pd
from langchain_experimental.text_splitter import SemanticChunker

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

    splitter = SemanticChunker(
        embeddings=get_embedder(),
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=10,
    )
    chunks = splitter.split_text(full_text)

    collection = _reset_collection(chroma, collection_name)

    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings = _embed_with_retry(batch)
        ids = [f"{collection_name}_{i + j}" for j in range(len(batch))]
        collection.add(ids=ids, embeddings=embeddings, documents=batch)

    return len(chunks)


_FOOD_DB_COLS = [
    "식품명", "영양성분함량기준량", "에너지(kcal)", "수분(g)", "단백질(g)", "지방(g)",
    "회분(g)", "탄수화물(g)", "당류(g)", "식이섬유(g)", "칼슘(mg)", "철(mg)",
    "인(mg)", "칼륨(mg)", "나트륨(mg)", "비타민A(μg RAE)", "레티놀(μg)",
    "베타카로틴(μg)", "티아민(mg)", "리보플라빈(mg)", "니아신(mg)", "비타민 C(mg)",
    "비타민 D(μg)", "콜레스테롤(mg)", "포화지방산(g)", "트랜스지방산(g)",
    "비타민 B12(μg)", "엽산(μg DFE)",
]


def ingest_excel(
    excel_path: str,
    collection_name: str,
    chroma: chromadb.ClientAPI,
) -> int:
    df = pd.read_excel(excel_path)
    df = df[[c for c in _FOOD_DB_COLS if c in df.columns]]

    names = df["식품명"].fillna("").astype(str).tolist()
    meta_cols = [c for c in df.columns if c != "식품명"]
    metadatas = [
        {k: str(v) for k, v in row.items() if pd.notna(v)}
        for _, row in df[meta_cols].iterrows()
    ]

    collection = _reset_collection(chroma, collection_name)

    batch_size = 100
    total = len(names)
    for i in range(0, total, batch_size):
        batch_names = names[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]
        embeddings = _embed_with_retry(batch_names)
        ids = [f"{collection_name}_{i + j}" for j in range(len(batch_names))]
        collection.add(ids=ids, embeddings=embeddings, documents=batch_names, metadatas=batch_meta)
        print(f"  [{collection_name}] {min(i + batch_size, total)}/{total}", end="\r")

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
