# Research Log — Hololog-AI

## 카테고리
- `CONFIG` — 설정 변경 (config.py, .env)
- `RAG` — RAG 파이프라인 (ingest, retriever, embedder)
- `AGENT` — LangGraph 에이전트
- `API` — FastAPI 엔드포인트
- `HARNESS` — Claude Code 하네스 (skills, hooks, agents)
- `BUG` — 버그 수정
- `IMPROVEMENT` — 기능 개선
- `SESSION` — 세션 구분

---

### 2026-06-13

- [IMPROVEMENT] 하네스 엔지니어링 초기 구성: claude.md, settings.json, skills(3), agents(2), log_research.py
- [IMPROVEMENT] uv init + 의존성 설치 (fastapi, langchain, langgraph, chromadb 등)
- [IMPROVEMENT] 앱 골격 구성: app/core, app/rag, app/agent, app/api — 전체 임포트 검증 통과
- [BUG] chromadb.PersistentClient가 팩토리 함수여서 타입 어노테이션 실패 → `from __future__ import annotations` 로 해결
- [AGENT] LangGraph 6노드 워크플로우 구성: fetch_ingredients→retrieve_context→generate_plan→validate_nutrition→check_budget→save_plan
- [API] FastAPI 라우트 등록: /agent/generate-plan, /health
- [IMPROVEMENT] WORKFLOW.md 작성

### 2026-06-14

- [IMPROVEMENT] LLM을 `init_chat_model`로 교체 — ChatOpenAI 제거, provider-agnostic 구조로 전환
- [CONFIG] LLM 모델 변경: gpt-4o → gemini-3.5-flash (Google GenAI)
- [RAG] embedder.py 생성 후 삭제 — `get_embedder()` lazy 팩토리를 config.py로 통합
- [RAG] retriever.py: OpenAI 직접 의존 제거 → `get_embedder()` 사용
- [RAG] ingest.py: OpenAI 직접 의존 제거 → `get_embedder()` 사용
- [CONFIG] config.py 단순화: `BaseSettings` → `BaseModel`, `apply_env()` 제거, `load_dotenv()` 사용
- [CONFIG] .env에 API 키만 관리, 나머지 설정은 config.py에서 직접 수정
- [CONFIG] 임베딩 모델 변경: text-embedding-3-small → gemini-embedding-2 (Google GenAI)
- [RAG] ingest.py: `langchain.text_splitter` → `langchain_text_splitters` 패키지 분리 대응
- [BUG] ingest.py: Google 임베딩 429 rate limit 대응 — `_embed_with_retry()` 추가 (60초 대기, 최대 3회 재시도)
- [HARNESS] log_research.py 개선: 파일 경로 기반 카테고리 자동 분류, 변경 내용 요약 추출

---

---
[2026-06-14 14:53] [SESSION] 세션 종료
---
[2026-06-14 15:04] [RAG] ingest.py 수정 — batch_size = 50
[2026-06-14 15:04] [RAG] ingest.py 수정 — batch_size = 100
[2026-06-14 15:05] [RAG] retriever.py 수정 — embedding = get_embedder().embed_query(f"task: search result...

---
[2026-06-14 15:05] [SESSION] 세션 종료
---

---
[2026-06-14 15:06] [SESSION] 세션 종료
---

---
[2026-06-14 15:07] [SESSION] 세션 종료
---

---
[2026-06-14 15:12] [SESSION] 세션 종료
---

---
[2026-06-14 16:11] [SESSION] 세션 종료
---

---
[2026-06-14 16:14] [SESSION] 세션 종료
---
[2026-06-14 16:19] [RAG] ingest.py 수정 — batch = chunks[i : i + batch_size]
[2026-06-14 16:19] [RAG] ingest.py 수정 — batch = texts[i : i + batch_size]
[2026-06-14 16:19] [RAG] retriever.py 수정 — embedding = get_embedder().embed_query(query)

---
[2026-06-14 16:19] [SESSION] 세션 종료
---

---
[2026-06-14 16:23] [SESSION] 세션 종료
---

---
[2026-06-14 16:29] [SESSION] 세션 종료
---
[2026-06-14 17:06] [IMPROVEMENT] .gitignore 수정 — chroma_db/

---
[2026-06-14 17:06] [SESSION] 세션 종료
---

---
[2026-06-14 17:07] [SESSION] 세션 종료
---

---
[2026-06-14 17:07] [SESSION] 세션 종료
---

---
[2026-06-14 17:08] [SESSION] 세션 종료
---

---
[2026-06-14 17:09] [SESSION] 세션 종료
---

---
[2026-06-14 17:11] [SESSION] 세션 종료
---

---
[2026-06-14 17:11] [SESSION] 세션 종료
---

---
[2026-06-16 20:50] [SESSION] 세션 종료
---

---
[2026-06-16 21:01] [SESSION] 세션 종료
---

---
[2026-06-16 21:14] [SESSION] 세션 종료
---

---
[2026-06-16 21:15] [SESSION] 세션 종료
---
[2026-06-16 21:19] [AGENT] nodes.py 수정 — from __future__ import annotations
[2026-06-16 21:20] [AGENT] nodes.py 수정 — async def _check_meal(meal: dict) -> dict | None:

---
[2026-06-16 21:21] [SESSION] 세션 종료
---
[2026-06-16 22:57] [RAG] ingest.py 수정 — collection.add(ids=ids, embeddings=embeddings, documents=bat...
[2026-06-16 22:57] [RAG] ingest.py 수정 — collection.add(ids=ids, embeddings=embeddings, documents=bat...

---
[2026-06-16 22:57] [SESSION] 세션 종료
---
[2026-06-16 22:59] [API] agent.py 수정 — import re
[2026-06-16 23:00] [API] agent.py 수정 — class GeneratePlanRequest(BaseModel):

---
[2026-06-16 23:01] [SESSION] 세션 종료
---

---
[2026-06-16 23:04] [SESSION] 세션 종료
---
[2026-06-16 23:06] [CONFIG] .env 수정 — LLM_API_KEY=AQ.Ab8RN6Ki1Pf3Pzkf2ekWqJAmGok-mp55ZQfTfhEfABSd3...
[2026-06-16 23:06] [CONFIG] config.py 수정 — load_dotenv()
[2026-06-16 23:06] [CONFIG] config.py 수정 — settings = get_settings()

---
[2026-06-16 23:07] [SESSION] 세션 종료
---
[2026-06-16 23:09] [CONFIG] config.py 수정 — llm_model: str = "claude-sonnet-4-6"
[2026-06-16 23:09] [HARNESS] ROOT_AGENT.md 수정 — - **LLM:** claude-sonnet-4-6 (Anthropic) via `init_chat_mode...

---
[2026-06-16 23:09] [SESSION] 세션 종료
---

---
[2026-06-16 23:13] [SESSION] 세션 종료
---

---
[2026-06-16 23:18] [SESSION] 세션 종료
---
[2026-06-16 23:31] [IMPROVEMENT] .gitkeep 작성

---
[2026-06-16 23:32] [SESSION] 세션 종료
---

---
[2026-06-16 23:35] [SESSION] 세션 종료
---

---
[2026-06-16 23:40] [SESSION] 세션 종료
---

---
[2026-06-16 23:41] [SESSION] 세션 종료
---

---
[2026-06-16 23:42] [SESSION] 세션 종료
---

---
[2026-06-16 23:44] [SESSION] 세션 종료
---
[2026-06-17 00:01] [RAG] ingest.py 수정 — _FOOD_DB_COLS = [

---
[2026-06-17 00:01] [SESSION] 세션 종료
---
[2026-06-17 00:06] [RAG] ingest.py 수정 — def ingest_excel(
[2026-06-17 00:06] [RAG] retriever.py 수정 — def search_joined(collection_name: str, query: str, n_result...
[2026-06-17 00:06] [AGENT] nodes.py 수정 — from app.rag.retriever import search_food, search_joined
[2026-06-17 00:07] [AGENT] nodes.py 수정 — menu = meal.get("menu_name", "")

---
[2026-06-17 00:07] [SESSION] 세션 종료
---

---
[2026-06-17 00:08] [SESSION] 세션 종료
---

---
[2026-06-17 00:08] [SESSION] 세션 종료
---

---
[2026-06-17 00:11] [SESSION] 세션 종료
---

---
[2026-06-17 00:13] [SESSION] 세션 종료
---

---
[2026-06-17 00:15] [SESSION] 세션 종료
---
[2026-06-17 00:18] [RAG] retriever.py 수정 — from __future__ import annotations
[2026-06-17 00:18] [RAG] retriever.py 수정 — def search_food(query: str, n_results: int = 5) -> str:

---
[2026-06-17 00:18] [SESSION] 세션 종료
---
[2026-06-17 00:27] [RAG] ingest.py 수정 — from langchain_text_splitters import SemanticChunker
[2026-06-17 00:27] [RAG] ingest.py 수정 — splitter = SemanticChunker(
[2026-06-17 00:35] [RAG] ingest.py 수정 — from langchain_experimental.text_splitter import SemanticChu...

---
[2026-06-17 00:35] [SESSION] 세션 종료
---

---
[2026-06-17 00:38] [SESSION] 세션 종료
---
[2026-06-17 00:42] [RAG] retriever.py 작성 — from __future__ import annotations
[2026-06-17 00:43] [AGENT] nodes.py 수정 — async def retrieve_context(state: AgentState) -> dict:
[2026-06-17 00:43] [AGENT] nodes.py 수정 — menu = meal.get("menu_name", "")
[2026-06-17 00:43] [AGENT] nodes.py 수정 — async def _save_meal(client, meal: dict, school_id: int) -> ...

---
[2026-06-17 00:44] [SESSION] 세션 종료
---

---
[2026-06-17 00:45] [SESSION] 세션 종료
---

---
[2026-06-17 00:54] [SESSION] 세션 종료
---

---
[2026-06-17 00:58] [SESSION] 세션 종료
---

---
[2026-06-17 01:03] [SESSION] 세션 종료
---
