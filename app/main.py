import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

_log = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.rag.retriever import _chroma_client, _get_bm25
    # ChromaDB: Windows Rust 바인딩 버그 방지용 메인 스레드 초기화
    _chroma_client()
    # BM25: 19,495건 인덱스 사전 로딩 — 첫 요청 레이턴시 제거
    try:
        await asyncio.to_thread(_get_bm25)
    except Exception as e:
        _log.warning("BM25 pre-warm skipped: %s", e)  # food_db 미구성 시에도 서버 시작 허용
    yield


app = FastAPI(
    title="Hololog-AI",
    description="학교 급식 AI 월간 식단 추천 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
