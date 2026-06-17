# Research Log — Hololog-AI

## 카테고리
- `CONFIG` — 설정 변경 (config.py, .env)
- `RAG` — RAG 파이프라인 (ingest, retriever, embedder)
- `AGENT` — LangGraph 에이전트
- `API` — FastAPI 엔드포인트
- `HARNESS` — Claude Code 하네스 (skills, hooks, agents)
- `BUG` — 버그 수정
- `IMPROVEMENT` — 기능 개선

---

## BUG

- [BUG] chromadb.PersistentClient가 팩토리 함수여서 타입 어노테이션 실패 → `from __future__ import annotations` 로 해결
- [BUG] Google 임베딩 429 rate limit 대응 — `_embed_with_retry()` 추가 (60초 대기, 최대 3회 재시도)
- [BUG] CORS `allow_credentials=True` + `allow_origins=["*"]` 조합은 스펙 위반 → `allow_credentials=False` 수정
- [BUG] `fetch_ingredients` 오류 시 그래프가 계속 진행하던 문제 → `generate_plan` 조기 반환 + `_after_generate` conditional edge 추가
- [BUG] `ingest.py` fitz.open() `with` 문 없어 예외 시 파일 핸들 누수 → `with fitz.open(...) as doc:` 수정
- [BUG] `_check_meal` LLM 응답 파싱을 `startswith("FAIL")` plain-text로 하던 문제 → `NutritionVerdict` Pydantic 구조화 출력으로 교체
- [BUG] `_embed_with_retry` 루프 후 명시적 반환 경로 없어 타입 체커 오류 → 루프 종료 후 `raise RuntimeError` 추가
- [BUG] `search_food` `collection.get()` 반환 순서가 RRF 랭킹과 불일치 → id_map 매핑 후 top_ids 순서대로 재구성
- [BUG] `_get_bm25` 다중 스레드 동시 초기화 경합 → `threading.Lock` 이중 확인 패턴 적용
- [BUG] `get_embedder()` 다중 스레드 동시 초기화 경합 → `threading.Lock` 이중 확인 패턴 적용

## IMPROVEMENT

- [IMPROVEMENT] LLM을 `init_chat_model`로 교체 — ChatOpenAI 제거, provider-agnostic 구조로 전환
- [IMPROVEMENT] `get_embedder()` lazy 팩토리를 config.py로 통합 (별도 embedder.py 제거)
- [IMPROVEMENT] config.py 단순화 — `BaseSettings` → `BaseModel`, `apply_env()` 제거, `load_dotenv()` 사용
- [IMPROVEMENT] ingest.py PDF 청킹: `RecursiveCharacterTextSplitter` → `SemanticChunker` (의미 기반 청킹)
- [IMPROVEMENT] retriever.py food_db 검색: 벡터 검색 단독 → BM25 + 벡터 하이브리드(RRF k=60) 로 정확도 개선
- [IMPROVEMENT] `fetch_ingredients`와 `retrieve_context` 병렬 실행 (LangGraph START fan-out) — 레이턴시 개선
- [IMPROVEMENT] `validate_nutrition` 동시 LLM 호출 수 `asyncio.Semaphore(5)` 로 제한 — rate limit 방지
- [IMPROVEMENT] `ingest_excel` 메타데이터 생성 `iterrows()` → `to_dict("records")` 로 교체 — 성능 개선
- [IMPROVEMENT] `pyproject.toml` 미사용 `pydantic-settings` 의존성 제거

---
[2026-06-17 19:30] [SESSION] 세션 종료
---

---
[2026-06-17 19:34] [SESSION] 세션 종료
---

---
[2026-06-17 19:34] [SESSION] 세션 종료
---

---
[2026-06-17 19:35] [SESSION] 세션 종료
---
[2026-06-17 19:36] [RAG] ingest.py 수정 — from langchain_text_splitters import SemanticChunker
[2026-06-17 19:37] [HARNESS] ingest-rag.md 수정 — ```bash

---
[2026-06-17 19:37] [SESSION] 세션 종료
---
[2026-06-17 19:39] [IMPROVEMENT] pyproject.toml 수정
[2026-06-17 19:39] [RAG] ingest.py 수정 — def ingest_pdf(
[2026-06-17 19:39] [RAG] ingest.py 수정 — def ingest_excel(
[2026-06-17 19:41] [RAG] ingest.py 수정 — from langchain_experimental.text_splitter import SemanticChu...
[2026-06-17 19:41] [IMPROVEMENT] pyproject.toml 수정 — "langchain-experimental>=0.4.2",

---
[2026-06-17 19:42] [SESSION] 세션 종료
---

---
[2026-06-17 19:43] [SESSION] 세션 종료
---

---
[2026-06-17 19:50] [SESSION] 세션 종료
---
[2026-06-17 20:07] [HARNESS] cli.py 작성 — """

---
[2026-06-17 20:07] [SESSION] 세션 종료
---
