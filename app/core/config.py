import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel

load_dotenv()
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "hololog-ai")

_PROVIDER_KEY_MAP = {
    "google_genai": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


class Settings(BaseModel):
    # LLM — 여기서 직접 수정
    llm_model: str = "claude-sonnet-4-6"
    llm_provider: str = "anthropic"  # google_genai | openai | anthropic

    # 임베딩 — 여기서 직접 수정
    embedding_provider: str = "huggingface"  # openai | google_genai | huggingface
    embedding_model: str = "BAAI/bge-m3"

    # Backend API
    backend_url: str = "http://localhost:8080"

    # ChromaDB
    chroma_db_path: str = "./chroma_db"

    # RAG 소스 파일
    policy_pdf_path: str = "./data/2026학년도학교급식기본계획.pdf"
    guidelines_pdf_path: str = "./data/학교급식_식단작성_참고자료 (1).pdf"
    food_db_excel_path: str = "./data/20251229_음식DB 19495건.xlsx"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# LLM_API_KEY → provider별 환경변수로 매핑 (config.py의 llm_provider 변경만으로 전환 가능)
_llm_api_key = os.environ.get("LLM_API_KEY", "")
if _llm_api_key and settings.llm_provider in _PROVIDER_KEY_MAP:
    os.environ.setdefault(_PROVIDER_KEY_MAP[settings.llm_provider], _llm_api_key)

_embedder: Embeddings | None = None


def get_embedder() -> Embeddings:
    global _embedder
    if _embedder is None:
        _embedder = init_embeddings(
            f"{settings.embedding_provider}:{settings.embedding_model}",
        )
    return _embedder
