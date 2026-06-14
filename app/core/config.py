import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel

load_dotenv()  # .env의 API 키를 os.environ에 직접 세팅
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "hololog-ai")


class Settings(BaseModel):
    # LLM — 여기서 직접 수정
    llm_model: str = "gemini-3.5-flash"
    llm_provider: str = "google_genai"  # google_genai | openai | anthropic

    # 임베딩 — 여기서 직접 수정
    embedding_provider: str = "huggingface"  # openai | google_genai | huggingface
    embedding_model: str = "BAAI/bge-m3"

    # Backend API
    backend_url: str = "http://localhost:8080"

    # ChromaDB
    chroma_db_path: str = "./chroma_db"

    # RAG 소스 파일
    policy_pdf_path: str = "./2026학년도학교급식기본계획.pdf"
    guidelines_pdf_path: str = "./학교급식_식단작성_참고자료.pdf"
    food_db_excel_path: str = "./20251229_음식DB 19495건.xlsx"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

_embedder: Embeddings | None = None


def get_embedder() -> Embeddings:
    global _embedder
    if _embedder is None:
        _embedder = init_embeddings(
            f"{settings.embedding_provider}:{settings.embedding_model}",
        )
    return _embedder
