# /run — FastAPI 개발 서버 실행

이 스킬은 Hololog-AI FastAPI 서버를 개발 모드로 실행합니다.

## 실행 전 체크리스트

1. **ChromaDB 초기화 여부 확인**
   - `chroma_db/` 디렉토리가 없으면 먼저 `/ingest-rag` 실행 필요

2. **환경변수 확인** (`.env` 파일 또는 시스템 환경변수)
   - `LANGCHAIN_API_KEY` — LangSmith 추적용
   - `LANGCHAIN_PROJECT` — LangSmith 프로젝트명 (예: `hololog-ai-dev`)
   - `OPENAI_API_KEY` — LLM 및 임베딩 (`text-embedding-3-small`)
   - `REDIS_URL` — Redis 연결 (기본: `redis://localhost:6379`)

3. **의존성 설치 여부**
   - 최초 실행 또는 `pyproject.toml` 변경 후: `uv sync` 실행 필요

## 실행 명령

```bash
uv run uvicorn app.main:app --reload --port 8000
```

## 서버 주소
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 문제 발생 시
- `ModuleNotFoundError`: `uv sync` 실행
- `Port already in use`: `--port 8001` 로 변경
- ChromaDB 오류: `/ingest-rag` 재실행
