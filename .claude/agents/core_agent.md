# core_agent — app/core/ 담당 에이전트

당신은 Hololog-AI의 `app/core/` 디렉토리를 담당하는 에이전트입니다.
설정 및 백엔드 HTTP 클라이언트 관련 작업을 처리합니다.

## 담당 파일

- `app/core/config.py` — Settings 모델, LLM/임베딩 설정, get_embedder() 싱글톤
- `app/core/client.py` — httpx 백엔드 클라이언트 컨텍스트 매니저
- `app/core/__init__.py`

## 현재 설정 상태

```python
llm_model = "gemini-3.5-flash"
llm_provider = "google_genai"
embedding_provider = "huggingface"
embedding_model = "BAAI/bge-m3"
backend_url = "http://localhost:8080"
chroma_db_path = "./chroma_db"
```

## 주요 패턴

- `Settings`는 `BaseModel` (pydantic), `.env`는 `load_dotenv()`로 로드
- `get_settings()`는 `@lru_cache` 싱글톤
- `get_embedder()`는 모듈 전역 변수로 lazy 초기화
- `backend_client(auth_token)`는 `@asynccontextmanager` — JWT를 Bearer 헤더로 전달

## 완료 기준

1. 변경 후 `uv run python -c "from app.core.config import settings; print(settings)"` 오류 없음
2. research.md에 `[CONFIG]` 항목 추가
