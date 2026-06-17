# Hololog-AI — 시스템 구조 및 동작 흐름

---

## 1. 프로젝트 개요

영양사가 `POST /agent/generate-plan`을 호출하면,  
AI Agent가 **보유 식자재 조회 → 영양 기준 검색(RAG) → 식단 생성(LLM) → 영양 검증 → 예산 확인 → 저장**  
순서로 월간 식단을 자동 작성해서 기존 백엔드 DB에 저장한다.

---

## 2. 디렉토리 구조

```
Hololog-AI/
│
├── app/                          # 서비스 메인 패키지
│   ├── main.py                   # FastAPI 앱 진입점
│   │
│   ├── core/                     # 인프라 레이어
│   │   ├── config.py             # 환경변수 설정 (pydantic-settings)
│   │   └── client.py             # 백엔드 API HTTP 클라이언트 (httpx)
│   │
│   ├── rag/                      # RAG 파이프라인
│   │   ├── ingest.py             # 문서 인덱싱 스크립트 (1회성 실행)
│   │   └── retriever.py          # ChromaDB 시맨틱 검색 유틸리티
│   │
│   ├── agent/                    # LangGraph AI Agent
│   │   ├── state.py              # 에이전트 상태 정의 (TypedDict)
│   │   ├── nodes.py              # 각 단계별 처리 함수 (6개 노드)
│   │   └── graph.py              # LangGraph 워크플로우 조립
│   │
│   └── api/
│       └── agent.py              # FastAPI 라우터 (/agent/generate-plan)
│
├── scripts/
│   └── log_research.py           # Claude Code 훅이 호출하는 로거
│
├── .claude/                      # Claude Code 하네스
│   ├── settings.json             # 권한 + 훅 설정
│   ├── skills/                   # 슬래시 명령어 (/run, /ingest-rag, /validate-plan)
│   └── agents/                   # 개발 서브에이전트 프롬프트 템플릿
│
├── chroma_db/                    # ChromaDB 로컬 저장소 (gitignore)
├── research.md                   # 개발 이력 자동 로그
├── claude.md                     # 프로젝트 개발 규칙
├── pyproject.toml                # uv 프로젝트 설정
└── .env                          # API 키 등 환경변수 (gitignore)
```

---

## 3. 핵심 컴포넌트 설명

### `app/core/config.py` — 설정 허브
- `load_dotenv()`로 `.env`를 로드, LangSmith 환경변수를 `os.environ`에 직접 세팅
- LLM/임베딩 모델은 `Settings` 클래스에서 직접 수정 (env 변경 불필요)
- `LLM_API_KEY` 하나로 provider 전환 지원 — `_PROVIDER_KEY_MAP`이 provider별 env 변수로 자동 매핑
  - `google_genai` → `GOOGLE_API_KEY`
  - `openai` → `OPENAI_API_KEY`
  - `anthropic` → `ANTHROPIC_API_KEY`

```
.env (LLM_API_KEY, LANGCHAIN_API_KEY)
  → load_dotenv()
  → Settings 객체 (lru_cache)
  → LLM_API_KEY를 llm_provider에 맞는 env 변수로 매핑
```

**현재 설정**
- LLM: `claude-sonnet-4-6` / provider: `anthropic`
- 임베딩: `BAAI/bge-m3` / provider: `huggingface` (로컬, API 키 불필요)

### `app/core/client.py` — 백엔드 API 클라이언트
- `httpx.AsyncClient`를 컨텍스트 매니저로 감싸서 제공
- 사용자의 JWT 토큰을 `Authorization: Bearer <token>` 헤더로 백엔드에 그대로 전달
- 모든 백엔드 API 호출(식자재, 식단 저장, 예산)에 사용

### `app/rag/ingest.py` — RAG 인덱싱 (1회성 실행)
- `uv run python app/rag/ingest.py` 로 실행
- 3개 소스 파일을 처리해서 ChromaDB에 저장

```
2026학년도학교급식기본계획.pdf  →  PyMuPDF 텍스트 추출
                                 →  SemanticChunker (langchain_experimental, 의미 기반 청킹)
                                 →  BAAI/bge-m3 (HuggingFace 로컬 임베딩)
                                 →  ChromaDB "policy" 컬렉션

학교급식_식단작성_참고자료.pdf   →  (동일 과정)
                                 →  ChromaDB "guidelines" 컬렉션

20251229_음식DB 19495건.xlsx    →  pandas 읽기 (to_dict)
                                 →  식품명 = document, 영양성분 = metadata
                                 →  BAAI/bge-m3 (HuggingFace 로컬 임베딩)
                                 →  ChromaDB "food_db" 컬렉션 (19,495개 문서)
```

### `app/rag/retriever.py` — ChromaDB 검색
- `search_joined(컬렉션명, 쿼리, n_results)` — policy/guidelines 컬렉션 벡터 검색, 결과를 하나의 문자열로 반환
- `search_food(쿼리, n_results)` — food_db 하이브리드 검색 (BM25 + 벡터, RRF k=60 병합), RRF 랭킹 순서 보존
- ChromaDB 클라이언트, 임베딩 모델, BM25 인덱스를 모듈 수준 싱글톤으로 관리 (`threading.Lock` 이중 확인으로 스레드 안전)

### `app/agent/state.py` — LangGraph 상태
LangGraph가 노드 간 데이터를 전달할 때 사용하는 공유 상태 객체.

```python
AgentState = {
    month: str,               # "2026-07"
    auth_token: str,          # 백엔드 JWT
    school_id: int,
    ingredients: list[dict],  # GET /ingredients 결과
    guidelines_context: str,  # RAG 검색 결과 (policy + guidelines)
    meal_plan: list[dict],    # LLM이 생성한 식단
    validation_errors: list,  # 영양 미달 항목
    budget_info: dict,        # GET /budgets 결과
    retry_count: int,         # 재생성 횟수 (최대 3)
    error: str | None,        # 치명적 오류
}
```

### `app/agent/nodes.py` — 6개 노드 함수
각 노드는 `AgentState`를 받아 변경할 필드만 `dict`로 반환한다.

| 노드 | 역할 |
|------|------|
| `fetch_ingredients` | `GET /ingredients` → `state.ingredients` |
| `retrieve_context` | RAG: policy + guidelines 검색 → `state.guidelines_context` |
| `generate_plan` | claude-sonnet-4-6 + 구조화 출력(Pydantic) → `state.meal_plan` |
| `validate_nutrition` | RAG: food_db 하이브리드 검색 + LLM `NutritionVerdict` 구조화 판단 → `state.validation_errors` (Semaphore(5) 병렬) |
| `check_budget` | `GET /budgets` → `state.budget_info` |
| `save_plan` | `POST /diets` + `POST /meals` × 식단 수 |

### `app/agent/graph.py` — LangGraph 워크플로우
노드들을 엣지로 연결하고 조건부 분기를 정의한다.

- `fetch_ingredients`와 `retrieve_context`는 START에서 **동시 fan-out** 후 `generate_plan`에서 합류
- `_after_generate`: `fetch_ingredients` 오류 시 `generate_plan` 이후 즉시 END로 라우팅
- `_should_regenerate`: 영양 검증 실패 시 최대 3회까지 `generate_plan`으로 루프

---

## 4. 동작 흐름 (End-to-End)

```
클라이언트 (영양사 앱)
    │
    │  POST /agent/generate-plan
    │  { "month": "2026-07", "school_id": 1 }
    │  Authorization: Bearer <JWT>
    ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI  (app/api/agent.py)                        │
│  - month YYYY-MM 포맷 검증 (field_validator)         │
│  - JWT 토큰 추출                                     │
│  - AgentState 초기화                                 │
│  - meal_plan_graph.ainvoke(state) 호출               │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  LangGraph 워크플로우 (app/agent/graph.py)           │
│                                                     │
│  ┌─ [1] fetch_ingredients ──────────────────────┐   │
│  │   └─ GET {BACKEND_URL}/ingredients           │   │
│  │   └─ state.ingredients 업데이트               │   │
│  │                                (병렬 실행)    │   │
│  └─ [2] retrieve_context ─────────────────────┐ │   │
│      └─ ChromaDB "policy" 검색                │ │   │
│      └─ ChromaDB "guidelines" 검색            │ │   │
│      └─ state.guidelines_context 업데이트     ┘ ┘   │
│                     │ (합류)                         │
│  [3] generate_plan  ┘                               │
│       (오류 있으면 → END)                            │
│       └─ 시스템 프롬프트: 영양사 전문가 역할           │
│       └─ 사용자 프롬프트:                            │
│           - 급식 일자 (해당 월 주중 날짜 목록)         │
│           - 영양 기준 (guidelines_context)           │
│           - 보유 식자재 (ingredients)                │
│           - 이전 검증 실패 항목 (재시도 시)            │
│       └─ claude-sonnet-4-6 with_structured_output   │
│       └─ state.meal_plan 업데이트                   │
│                     │                               │
│  [4] validate_nutrition                             │
│       └─ 각 메뉴마다 ChromaDB "food_db" 검색         │
│       └─ asyncio.gather로 LLM 판단 병렬 실행         │
│           (에너지 1/3, 단백질 7~20%,                 │
│            지방 15~30%, 나트륨 1000mg 이하)           │
│       └─ state.validation_errors 업데이트            │
│                     │                               │
│         ┌───────────┴──────────────┐               │
│    오류 있음 && retry < 3       오류 없음            │
│         │                          │               │
│    [3]으로 돌아가 재생성        [5] check_budget     │
│    (최대 3회)                       └─ GET /budgets │
│                                     └─ state.budget_info 업데이트
│                                          │          │
│                                   [6] save_plan     │
│                                     └─ 식단마다:    │
│                                         POST /diets │
│                                         POST /meals │
└─────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI 응답                                        │
│  {                                                  │
│    "month": "2026-07",                              │
│    "total_meals": 66,  (22일 × 3끼)                │
│    "meal_plan": [...],                              │
│    "validation_errors": [...],                      │
│    "budget_info": {...},                            │
│    "error": null                                    │
│  }                                                  │
└─────────────────────────────────────────────────────┘
```

---

## 5. RAG 3개 컬렉션 역할 분리

| 컬렉션 | 사용 노드 | 용도 |
|--------|----------|------|
| `policy` | `retrieve_context` | 영양 기준량, 급식 정책 |
| `guidelines` | `retrieve_context` | 식단 작성 가이드라인, 구성 원칙 |
| `food_db` | `validate_nutrition` | 개별 식품 영양 성분 조회 |

`policy`와 `guidelines`는 식단 **생성 전** 기준 컨텍스트로 사용하고,  
`food_db`는 생성 **후** 각 메뉴의 영양소를 추정·검증하는 데 사용한다.

---

## 6. LangSmith 추적

`config.py`가 import될 때 자동으로 `LANGCHAIN_TRACING_V2=true`가 설정된다.  
이후 모든 LangChain/LangGraph 호출은 LangSmith 대시보드에서 추적 가능하다.

- 추적 대상: `generate_plan` (LLM 호출), `validate_nutrition` (LLM 호출 × 메뉴 수)
- LangSmith 프로젝트명: `hololog-ai` (`.env`에서 변경 가능)

---

## 7. 개발 시작 순서

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일에 LLM_API_KEY, LANGCHAIN_API_KEY 입력

# 2. RAG 인덱싱 (최초 1회)
uv run python -m app.rag.ingest

# 3. 개발 서버 실행
uv run uvicorn app.main:app --reload --port 8000

# 4. API 테스트
# http://localhost:8000/docs 에서 Swagger UI 확인
```

---

## 8. 주요 의존성

| 패키지 | 버전 | 역할 |
|--------|------|------|
| `fastapi` | 0.136 | API 서버 |
| `langgraph` | 1.2 | 에이전트 워크플로우 상태 머신 |
| `langchain` | 1.3 | LLM/임베딩 추상화 (`init_chat_model`) |
| `langchain-anthropic` | - | claude-sonnet-4-6 호출, 구조화 출력 |
| `langchain-experimental` | 0.4 | SemanticChunker (의미 기반 PDF 청킹) |
| `langchain-huggingface` | 1.2 | BAAI/bge-m3 로컬 임베딩 |
| `langsmith` | 0.8 | LLM 호출 추적/모니터링 |
| `chromadb` | 1.5 | 로컬 벡터 데이터베이스 |
| `rank-bm25` | 0.2 | food_db BM25 하이브리드 검색 |
| `pymupdf` | 1.27 | PDF 텍스트 추출 |
| `pandas` | 3.0 | Excel 음식DB 처리 |
| `httpx` | 0.28 | 백엔드 API 비동기 HTTP 클라이언트 |
