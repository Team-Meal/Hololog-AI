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
