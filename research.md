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

---
[2026-06-17 20:08] [SESSION] 세션 종료
---
[2026-06-30 14:22] [IMPROVEMENT] app/scoring 패키지 신설 — 룰 기반 식자재 스코어링(3.2), 5개 지표 산식(4.2), KAMIS 선택적 연동
  - seasonal.py: 농사로 기준 월별 제철 식재료 하드코딩 (12개월 × 15~20종)
  - kamis.py: KAMIS_API_KEY 설정 시 당일가격/평년가격 비율로 0~1 점수 산출, 키 미설정 시 0.5 반환
  - scorer.py: 제철(0.30)·가격(0.25)·재고(0.30)·선호(0.10)·예산(0.05) 가중합, [학교재고]/[농사로]/[KAMIS] 태그 부여
  - metrics.py: 지역농산물활용률·제철반영률·1인단가·폐기감소율·예산절감율 순수 함수 정의
[2026-06-30 14:22] [AGENT] generate_single_meal 프롬프트 수정 — scored_ingredients 상위 10개 + 출처 태그 규칙 삽입
[2026-06-30 14:22] [AGENT] 노드 4개 추가 — score_ingredients_single, score_ingredients, generate_qa(7.4 Q&A 6개), compute_metrics
[2026-06-30 14:22] [AGENT] 그래프 배선 변경 — 단건: resolve/retrieve → score → generate → validate → generate_qa → budget → save; 월간: fetch → score → generate, budget → compute_metrics → save
[2026-06-30 14:22] [API] RecommendMealResponse에 qa_pairs·meal_metrics 추가; GeneratePlanResponse에 meal_metrics 추가

---
[2026-06-17 20:08] [SESSION] 세션 종료
---
[2026-06-17 20:09] [IMPROVEMENT] cli.py 수정 — """
[2026-06-17 20:09] [IMPROVEMENT] .gitignore 수정 — .pytest_cache/

---
[2026-06-17 20:09] [SESSION] 세션 종료
---

---
[2026-06-17 20:10] [SESSION] 세션 종료
---

---
[2026-06-17 20:10] [SESSION] 세션 종료
---
[2026-06-17 20:11] [IMPROVEMENT] mock_backend.py 작성 — """

---
[2026-06-17 20:11] [SESSION] 세션 종료
---
[2026-06-17 20:12] [IMPROVEMENT] mock_backend.py 수정 — if __name__ == "__main__":

---
[2026-06-17 20:13] [SESSION] 세션 종료
---
[2026-06-17 20:13] [IMPROVEMENT] __init__.py 작성

---
[2026-06-17 20:13] [SESSION] 세션 종료
---

---
[2026-06-17 20:15] [SESSION] 세션 종료
---

---
[2026-06-17 20:15] [SESSION] 세션 종료
---
[2026-06-17 20:19] [RAG] retriever.py 수정 — vec = collection.query(

---
[2026-06-17 20:19] [SESSION] 세션 종료
---
[2026-06-17 20:22] [API] main.py 수정 — from contextlib import asynccontextmanager

---
[2026-06-17 20:22] [SESSION] 세션 종료
---
[2026-06-17 20:43] [AGENT] state.py 수정 — from typing import TypedDict
[2026-06-17 20:43] [API] agent.py 수정 — import calendar
[2026-06-17 20:43] [API] agent.py 수정 — initial_state: AgentState = {
[2026-06-17 20:43] [AGENT] nodes.py 수정 — import asyncio
[2026-06-17 20:44] [AGENT] nodes.py 수정 — async def retrieve_context(state: AgentState) -> dict:
[2026-06-17 20:45] [AGENT] nodes.py 수정 — _MEAL_TYPES = ["BREAKFAST", "LUNCH", "DINNER"]

---
[2026-06-17 20:46] [SESSION] 세션 종료
---
[2026-06-17 20:47] [API] agent.py 수정 — import calendar

---
[2026-06-17 20:48] [SESSION] 세션 종료
---

---
[2026-06-17 20:49] [SESSION] 세션 종료
---

---
[2026-06-17 21:05] [SESSION] 세션 종료
---
[2026-06-17 21:09] [AGENT] nodes.py 수정 — from __future__ import annotations
[2026-06-17 21:09] [AGENT] nodes.py 수정 — class MealItem(BaseModel):
[2026-06-17 21:09] [AGENT] nodes.py 수정 — class MealVerdict(BaseModel):
[2026-06-17 21:09] [AGENT] nodes.py 수정 — async def fetch_ingredients(state: AgentState) -> dict:
[2026-06-17 21:09] [AGENT] nodes.py 수정 — structured = _get_llm().with_structured_output(MonthlyMealPl...
[2026-06-17 21:09] [AGENT] nodes.py 수정 — async def validate_nutrition(state: AgentState) -> dict:
[2026-06-17 21:10] [AGENT] graph.py 수정 — def _should_regenerate(state: AgentState) -> str:
[2026-06-17 21:10] [AGENT] graph.py 수정 — g.add_conditional_edges(
[2026-06-17 21:10] [API] agent.py 수정 — if final_state.get("error"):
[2026-06-17 21:10] [RAG] retriever.py 수정 — _chroma: chromadb.ClientAPI | None = None

---
[2026-06-17 21:10] [SESSION] 세션 종료
---
[2026-06-17 21:12] [AGENT] nodes.py 수정 — import asyncio
[2026-06-17 21:12] [AGENT] nodes.py 수정 — errors = [

---
[2026-06-17 21:13] [SESSION] 세션 종료
---

---
[2026-06-17 21:13] [SESSION] 세션 종료
---
[2026-06-18 16:57] [AGENT] nodes.py 수정 — school_day_set = set(school_days)
[2026-06-18 16:57] [AGENT] nodes.py 수정 — async def _save_meal(client, meal: dict, school_id: int) -> ...
[2026-06-18 16:57] [IMPROVEMENT] mock_backend.py 수정 — @app.post("/diets", status_code=201)
[2026-06-18 16:57] [CONFIG] config.py 수정 — class Settings(BaseModel):

## 2026-06-18 추가 수정

- [IMPROVEMENT] `generate_plan`: (date, meal_type) 중복 제거 로직 추가 — first-wins 방식으로 LLM 중복 출력 방어
- [IMPROVEMENT] `validate_nutrition`: 코드 레벨 영양 수치 검증 추가 — 나트륨>1000mg, 에너지<200kcal, 단백질/지방 비율(7~20%/15~30%) 이탈 시 errors에 추가. LLM 이중 판정 방지를 위해 `already_failed` set 활용
- [IMPROVEMENT] `validate_nutrition`: 완전성 검사 추가 — `state["school_days"] × _MEAL_TYPES` 에서 누락된 (날짜,끼니) 조합을 오류로 추가해 재시도 유발
- [IMPROVEMENT] `save_plan` + `_save_meal`: 저장 실패 시 성공한 diet들 롤백 — `DELETE /diets/{id}` 호출로 고아 레코드 방지. 실제 백엔드도 해당 엔드포인트 필요
- [IMPROVEMENT] `test/mock_backend.py`: 인메모리 저장소(_diets, _meals) 추가 + `DELETE /diets/{diet_id}` 엔드포인트 추가 (연관 meals cascade 삭제)
- [CONFIG] `app/core/config.py`: Settings 필드를 `os.getenv` 기반으로 변경 — 코드 수정 없이 .env 또는 환경변수로 모델/URL/경로 제어 가능
- [CONFIG] `.env.example` 신규 생성 — 배포 환경 설정 참고용

---
[2026-06-18 16:58] [SESSION] 세션 종료
---

---
[2026-06-18 17:01] [SESSION] 세션 종료
---

---
[2026-06-18 17:05] [SESSION] 세션 종료
---
[2026-06-18 17:11] [AGENT] nodes.py 수정 — _MEAL_TYPES = ["BREAKFAST", "LUNCH", "DINNER"]
[2026-06-18 17:11] [AGENT] nodes.py 수정 — policy, guidelines = await asyncio.gather(
[2026-06-18 17:12] [AGENT] nodes.py 수정 — async def validate_nutrition(state: AgentState) -> dict:
[2026-06-18 17:12] [API] main.py 수정 — import asyncio

---
[2026-06-18 17:12] [SESSION] 세션 종료
---

---
[2026-06-18 17:18] [SESSION] 세션 종료
---
[2026-06-18 17:51] [AGENT] state.py 수정 — from typing import TypedDict
[2026-06-18 17:51] [AGENT] nodes.py 수정 — from app.agent.state import AgentState, SingleMealState
[2026-06-18 17:52] [AGENT] graph.py 수정 — from langgraph.graph import END, START, StateGraph
[2026-06-18 17:52] [AGENT] graph.py 수정 — meal_plan_graph = build_graph().compile()
[2026-06-18 17:52] [API] agent.py 수정 — import calendar

---
[2026-06-18 17:52] [SESSION] 세션 종료
---

---
[2026-06-18 17:53] [SESSION] 세션 종료
---

---
[2026-06-18 17:54] [SESSION] 세션 종료
---

---
[2026-06-18 17:54] [SESSION] 세션 종료
---
[2026-06-18 17:58] [RAG] retriever.py 수정 — vec_ids_raw = vec.get("ids", [[]])
[2026-06-18 17:58] [AGENT] nodes.py 수정 — diet_resp.raise_for_status()
[2026-06-18 17:58] [IMPROVEMENT] mock_backend.py 수정 — from fastapi import FastAPI, HTTPException
[2026-06-18 17:58] [IMPROVEMENT] mock_backend.py 수정 — @app.delete("/diets/{diet_id}")
[2026-06-18 17:58] [API] main.py 수정 — import asyncio
[2026-06-18 17:58] [API] main.py 수정 — try:

## 2026-06-18 전체 파일 버그 점검

- [BUG] `search_food` 빈 ChromaDB 컬렉션 시 `vec["ids"][0]` IndexError → 빈 결과 early return guard 추가 (`retriever.py`)
- [BUG] `_save_meal` 백엔드 응답에 `id` 필드 없을 때 `diet_id=None` 이 그대로 통과 → None 즉시 ValueError raise (`nodes.py`)
- [BUG] `delete_diet` 존재하지 않는 ID에 200 반환 → 404 HTTPException 추가 (`mock_backend.py`)
- [BUG] BM25 초기화 실패 시 `except: pass` 침묵 → `logging.warning`으로 실패 원인 출력 (`main.py`)
- 의도적 설계 유지: `_get_llm` non-thread-safe(CPython GIL 안전), `retry_count` 의미(3회=추가 시도), `_bm25_ids` 무락 읽기(재초기화 경로 없음), rollback `except: pass`(원 오류 마스킹 방지)

## 2026-06-18 토큰·레이턴시 최적화

- [BUG] `SingleMealPlan` 영양 추정치 기본값 `0` → `None` — LLM이 필드 생략 시 `kcal=0`이 되어 `validate_single_nutrition`에서 무한 재시도 유발. `validate_single_nutrition` guard도 `is not None` 조건으로 수정 (`nodes.py`)
- [IMPROVEMENT] `validate_nutrition` / `validate_single_nutrition`: food_db 검색 결과 LLM 프롬프트 삽입 시 문서당 300자 제한 추가 — 월간 60끼니 × 미제한 food_db 문서로 인한 토큰 폭증 방지 (`nodes.py`)
- [IMPROVEMENT] `generate_plan`: `ingredients_text` 3000자 상한 추가 — 학교 보유 식자재 수 제한 없어 토큰 폭증 가능 (`nodes.py`)
- [IMPROVEMENT] `save_single_plan`: 메뉴 항목 /meals POST 순차 for 루프 → `asyncio.gather`로 병렬화 — 월간 `save_plan`과 패턴 일치, 4~5개 요청 순차 대기 제거 (`nodes.py`)
- [IMPROVEMENT] `search_food`: BM25+벡터 검색 순차 실행 → `ThreadPoolExecutor(max_workers=2)` 병렬 실행 — BM25(numpy GIL 해제)와 ChromaDB Rust 바인딩(GIL 해제) 모두 병렬 가능 (`retriever.py`)
- [BUG] `search_food`: 벡터 결과 빈 경우 `return ""` 조기 종료 → BM25 결과도 버려지던 버그. `vec_ids = []`로 설정해 BM25 단독 RRF 진행으로 수정 (`retriever.py`)
- 의도적 설계 유지: LangGraph fan-out join(자동 배리어 조인, 레이스 아님), client.py 1회성 AsyncClient(auth_token이 요청마다 달라 싱글톤 불가), check_budget 미사용 결과(향후 예산 초과 차단 스캐폴딩)

---
[2026-06-18 17:58] [SESSION] 세션 종료
---

---
[2026-06-18 18:04] [SESSION] 세션 종료
---

---
[2026-06-18 18:05] [SESSION] 세션 종료
---

---
[2026-06-18 18:08] [SESSION] 세션 종료
---

---
[2026-06-18 18:09] [SESSION] 세션 종료
---

---
[2026-06-18 18:09] [SESSION] 세션 종료
---
[2026-06-18 18:21] [AGENT] state.py 수정 — class SingleMealState(TypedDict):
[2026-06-18 18:21] [AGENT] nodes.py 수정 — class SingleMealPlan(BaseModel):
[2026-06-18 18:22] [AGENT] nodes.py 수정 — structured = _get_llm().with_structured_output(SingleMealPla...
[2026-06-18 18:22] [AGENT] graph.py 수정 — from app.agent.nodes import (
[2026-06-18 18:22] [AGENT] graph.py 수정 — def _after_single_generate(state: SingleMealState) -> str:
[2026-06-18 18:22] [API] agent.py 수정 — class RecommendMealRequest(BaseModel):
[2026-06-18 18:23] [API] agent.py 수정 — initial_state: SingleMealState = {

---
[2026-06-18 18:23] [SESSION] 세션 종료
---

---
[2026-06-18 18:24] [SESSION] 세션 종료
---

---
[2026-06-18 18:25] [SESSION] 세션 종료
---

---
[2026-06-18 18:25] [SESSION] 세션 종료
---
[2026-06-18 18:51] [AGENT] nodes.py 수정 — class SingleMealPlan(BaseModel):
[2026-06-18 18:51] [AGENT] nodes.py 수정 — ingredients_text = (
[2026-06-18 18:51] [AGENT] nodes.py 수정 — lines = [
[2026-06-18 18:52] [AGENT] nodes.py 수정 — lines = [
[2026-06-18 18:52] [AGENT] nodes.py 수정 — n = len(menus)
[2026-06-18 18:52] [RAG] retriever.py 수정 — from __future__ import annotations
[2026-06-18 18:52] [RAG] retriever.py 수정 — fetch = n_results * 2
[2026-06-18 18:53] [AGENT] nodes.py 수정 — async def _post_meal(menu):

---
[2026-06-18 18:53] [SESSION] 세션 종료
---

---
[2026-06-18 18:59] [SESSION] 세션 종료
---

---
[2026-06-18 19:10] [SESSION] 세션 종료
---

---
[2026-06-18 19:11] [SESSION] 세션 종료
---
[2026-06-18 19:14] [IMPROVEMENT] cli.py 작성 — """

---
[2026-06-18 19:14] [SESSION] 세션 종료
---
[2026-06-29 13:12] [AGENT] nodes.py 수정 — from __future__ import annotations
[2026-06-29 13:12] [AGENT] nodes.py 수정 — async def fetch_ingredients(state: AgentState) -> dict:
[2026-06-29 13:12] [AGENT] nodes.py 수정 — structured = _get_llm().with_structured_output(MonthlyMealPl...
[2026-06-29 13:13] [AGENT] nodes.py 수정 — structured = _get_llm().with_structured_output(BatchNutritio...
[2026-06-29 13:13] [RAG] retriever.py 수정 — def search(collection_name: str, query: str, n_results: int ...
[2026-06-29 13:13] [RAG] retriever.py 수정 — try:
[2026-06-29 13:13] [RAG] ingest.py 수정 — from __future__ import annotations
[2026-06-29 13:13] [RAG] ingest.py 수정 — except Exception as e:
[2026-06-29 13:13] [RAG] ingest.py 수정 — def ingest_pdf(
[2026-06-29 13:13] [RAG] ingest.py 수정 — def ingest_excel(
[2026-06-29 13:13] [API] agent.py 수정 — import asyncio
[2026-06-29 13:13] [API] agent.py 수정 — try:

---
[2026-06-29 13:14] [SESSION] 세션 종료
---
[2026-06-29 13:18] [AGENT] nodes.py 수정 — if _llm is None:
[2026-06-29 13:18] [AGENT] nodes.py 수정 — structured = _get_llm().with_structured_output(BatchNutritio...
[2026-06-29 13:19] [AGENT] nodes.py 수정 — if result is not None:
[2026-06-29 13:19] [API] agent.py 수정 — from app.agent.graph import meal_plan_graph, single_meal_gra...
[2026-06-29 13:19] [IMPROVEMENT] research.md 수정 — ---
[2026-06-29 13:20] [IMPROVEMENT] research.md 수정 — ---

---
[2026-06-29 13:21] [SESSION] 세션 종료
---

---
[2026-06-29 13:24] [SESSION] 세션 종료
---

---
[2026-06-30 14:01] [SESSION] 세션 종료
---
[2026-06-30 14:15] [IMPROVEMENT] __init__.py 작성
[2026-06-30 14:16] [IMPROVEMENT] seasonal.py 작성 — """
[2026-06-30 14:16] [IMPROVEMENT] metrics.py 작성 — """
[2026-06-30 14:16] [CONFIG] config.py 수정 — llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2")...
[2026-06-30 14:16] [IMPROVEMENT] kamis.py 작성 — """
[2026-06-30 14:16] [IMPROVEMENT] scorer.py 작성 — """
[2026-06-30 14:17] [AGENT] state.py 수정 — class AgentState(TypedDict):
[2026-06-30 14:17] [AGENT] nodes.py 수정 — from app.agent.state import AgentState, SingleMealState
[2026-06-30 14:18] [AGENT] graph.py 수정 — from app.agent.nodes import (
[2026-06-30 14:18] [AGENT] graph.py 수정 — def build_graph() -> StateGraph:
[2026-06-30 14:19] [AGENT] graph.py 수정 — def _should_single_regenerate(state: SingleMealState) -> str...
[2026-06-30 14:19] [API] agent.py 수정 — class GeneratePlanResponse(BaseModel):
[2026-06-30 14:19] [API] agent.py 수정 — class RecommendMealResponse(BaseModel):
[2026-06-30 14:19] [API] agent.py 수정 — initial_state: SingleMealState = {
[2026-06-30 14:19] [API] agent.py 수정 — return RecommendMealResponse(
[2026-06-30 14:19] [API] agent.py 수정 — initial_state: AgentState = {
[2026-06-30 14:19] [API] agent.py 수정 — return GeneratePlanResponse(
[2026-06-30 14:23] [IMPROVEMENT] research.md 수정 — ---

---
[2026-06-30 14:23] [SESSION] 세션 종료
---
