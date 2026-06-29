# Hololog-AI — 시스템 구조 및 동작 흐름

---

## 1. 프로젝트 개요

두 가지 AI 식단 생성 엔드포인트를 제공한다.

**단건 식단 추천** (`POST /agent/recommend-meal`)  
날짜·끼니 하나를 요청하면 RAG 급식 규정 기반으로 밥·국·반찬 구성을 생성하고,  
영양 검증 → 예산 확인 → 백엔드 저장까지 수행한다. 검증 실패 시 최대 3회 재생성.

**월간 식단 생성** (`POST /agent/generate-plan`)  
AI Agent가 **보유 식자재 조회 → 영양 기준 검색(RAG) → 식단 생성(LLM) → 영양 검증 → 예산 확인 → 저장**  
순서로 월간 식단(조식·중식·석식)을 자동 작성해서 기존 백엔드 DB에 저장한다.  
주말·한국 공휴일·학교 재량휴업일은 자동 제외되며, 검증 실패 시 최대 3회 재생성을 시도한다.

두 그래프는 **구조가 동일**하다. 차이는 범위(1끼 vs 월간)와 초기 데이터 수집 방식뿐이다.

---

## 2. 디렉토리 구조

```
Hololog-AI/
│
├── app/                          # 서비스 메인 패키지
│   ├── main.py                   # FastAPI 앱 진입점 (lifespan: ChromaDB 사전 초기화)
│   │
│   ├── core/                     # 인프라 레이어
│   │   ├── config.py             # 환경변수 설정 (os.getenv + .env)
│   │   └── client.py             # 백엔드 API HTTP 클라이언트 (httpx, 요청마다 새 클라이언트)
│   │
│   ├── rag/                      # RAG 파이프라인
│   │   ├── ingest.py             # 문서 인덱싱 스크립트 (1회성 실행)
│   │   └── retriever.py          # ChromaDB 검색 유틸리티 (BM25+벡터 병렬 하이브리드)
│   │
│   ├── agent/                    # LangGraph AI Agent
│   │   ├── state.py              # 에이전트 상태 정의 (AgentState, SingleMealState)
│   │   ├── nodes.py              # 각 단계별 처리 함수 (12개 노드)
│   │   └── graph.py              # LangGraph 워크플로우 (meal_plan_graph, single_meal_graph)
│   │
│   └── api/
│       └── agent.py              # FastAPI 라우터 (/agent/recommend-meal, /agent/generate-plan)
│
├── test/                         # 로컬 테스트 도구
│   ├── __init__.py               # 패키지 초기화
│   ├── cli.py                    # CLI 테스트 스크립트 (uv run python test/cli.py)
│   ├── mock_backend.py           # 로컬 Mock 백엔드 서버 (port 8080)
│   └── result/                   # CLI 실행 결과 JSON 저장 (gitignore)
│
├── scripts/
│   └── log_research.py           # Claude Code 훅이 호출하는 로거
│
├── .claude/                      # Claude Code 하네스
│   ├── settings.json             # 권한 + 훅 설정
│   ├── skills/                   # 슬래시 명령어
│   └── agents/                   # 개발 서브에이전트 프롬프트 템플릿
│
├── chroma_db/                    # ChromaDB 로컬 저장소 (gitignore)
├── data/                         # RAG 원본 파일 (gitignore)
├── research.md                   # 개발 이력 자동 로그
├── CLAUDE.md                     # 프로젝트 개발 규칙
├── WORKFLOW.md                   # 이 파일
├── .env                          # API 키 등 환경변수 (gitignore)
├── .env.example                  # 환경변수 목록 참고용 (git 포함)
└── pyproject.toml                # uv 프로젝트 설정
```

---

## 3. 핵심 컴포넌트 설명

### `app/core/config.py` — 설정 허브
- `load_dotenv()`로 `.env`를 로드, LangSmith 환경변수를 `os.environ`에 세팅
- **모든 필드가 `os.getenv(변수명, 기본값)` 기반** — 코드 수정 없이 `.env`로 모델/URL/경로 제어
- `LLM_API_KEY` 하나로 provider 전환 지원 — `_PROVIDER_KEY_MAP`이 provider별 env 변수로 자동 매핑

```
.env (LLM_API_KEY, BACKEND_URL, ...)
  → load_dotenv()
  → os.getenv()
  → Settings 객체 (lru_cache)
  → LLM_API_KEY를 llm_provider에 맞는 env 변수로 매핑
```

**주요 환경변수**

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `LLM_PROVIDER` | `anthropic` | `openai` \| `google_genai` \| `anthropic` |
| `LLM_MODEL` | `claude-sonnet-4-6` | 사용할 LLM 모델 ID |
| `LLM_API_KEY` | — | provider별 API 키 |
| `EMBEDDING_PROVIDER` | `huggingface` | 임베딩 provider |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 임베딩 모델 |
| `BACKEND_URL` | `http://localhost:8080` | 기존 백엔드 주소 |
| `CHROMA_DB_PATH` | `./chroma_db` | ChromaDB 저장 경로 |

### `app/main.py` — FastAPI 진입점
- **lifespan**: 서버 시작 시 ChromaDB를 메인 스레드에서 사전 초기화
  - Windows에서 ChromaDB Rust 바인딩이 비동기 워커 스레드에서 실패하는 버그 우회
  - BM25 인덱스 사전 로딩 (첫 요청 레이턴시 제거). 실패 시 `logging.warning` 출력 후 서버 시작 허용
- CORS 미들웨어 포함

### `app/core/client.py` — 백엔드 API 클라이언트
- `httpx.AsyncClient`를 컨텍스트 매니저(`backend_client(auth_token)`)로 제공
- 사용자 JWT를 `Authorization: Bearer <token>`으로 백엔드에 그대로 전달
- auth_token이 요청마다 달라 싱글톤 불가 — 요청마다 새 클라이언트 생성

### `app/rag/ingest.py` — RAG 인덱싱 (1회성 실행)
- `uv run python -m app.rag.ingest` 로 실행 (로컬 또는 서버에서 1회)

```
2026학년도학교급식기본계획.pdf  →  PyMuPDF 텍스트 추출
                                 →  SemanticChunker (의미 기반 청킹)
                                 →  BAAI/bge-m3 (HuggingFace 로컬 임베딩)
                                 →  ChromaDB "policy" 컬렉션

학교급식_식단작성_참고자료.pdf   →  (동일 과정)
                                 →  ChromaDB "guidelines" 컬렉션

20251229_음식DB 19495건.xlsx    →  pandas to_dict("records")
                                 →  식품명 = document, 영양성분 = metadata
                                 →  BAAI/bge-m3 임베딩
                                 →  ChromaDB "food_db" 컬렉션 (19,495건)
```

### `app/rag/retriever.py` — ChromaDB 검색
- `search_joined(컬렉션명, 쿼리, n)` — policy/guidelines 컬렉션 벡터 검색
- `search_food(쿼리, n)` — food_db 하이브리드 검색
  - embedding 1회 수행 후 BM25(numpy)와 벡터(Rust 바인딩)를 **ThreadPoolExecutor로 병렬 실행**
  - RRF k=60으로 결과 병합. 벡터 결과 빈 경우 BM25 단독으로 fallback
- ChromaDB 클라이언트, BM25 인덱스를 싱글톤으로 관리 (`threading.Lock` 이중 확인, 스레드 안전)

### `app/agent/state.py` — LangGraph 상태

**월간 식단 그래프용**
```python
AgentState = {
    month: str,               # "2026-07"
    auth_token: str,          # 백엔드 JWT
    school_id: int,
    school_days: list[str],   # 급식 제공 날짜 목록 (주말·공휴일·재량휴업일 제외)
    ingredients: list[dict],  # GET /ingredients 결과
    guidelines_context: str,  # RAG 검색 결과 (policy + guidelines)
    meal_plan: list[dict],    # LLM이 생성한 식단
    validation_errors: list,  # 영양 미달 / 누락 항목
    budget_info: dict,        # GET /budgets 결과
    retry_count: int,         # 재생성 횟수 (최대 3)
    error: str | None,        # 치명적 오류
}
```

**단건 식단 그래프용**
```python
SingleMealState = {
    meal_date: str,                    # "2026-07-01"
    meal_type: str,                    # "BREAKFAST" | "LUNCH" | "DINNER"
    auth_token: str,
    school_id: int,
    target_calories: int | None,       # 목표 칼로리 (없으면 자유)
    serving_count: int,                # 급식 인원
    budget_limit: int | None,          # 예산 제한 (없으면 자유)
    excluded_ingredient_ids: list[int],# 제외 식자재 ID 목록
    excluded_names: list[str],         # ID → 이름 변환 결과
    guidelines_context: str,           # RAG 검색 결과
    result: dict | None,               # LLM 생성 결과 (menus + reason + 영양 추정치)
    validation_errors: list,           # 영양 검증 실패 항목
    retry_count: int,                  # 재생성 횟수 (최대 3)
    budget_info: dict,                 # GET /budgets 결과
    error: str | None,
}
```

### `app/agent/nodes.py` — 12개 노드 함수

**월간 식단 그래프 (meal_plan_graph)**

| 노드 | 역할 |
|------|------|
| `fetch_ingredients` | `GET /ingredients` → `state.ingredients` (3회 재시도) |
| `retrieve_context` | RAG: policy(영양기준) + guidelines(식단가이드) 병렬 검색 → `state.guidelines_context` |
| `generate_plan` | LLM(구조화 출력) → 조식·중식·석식 × 급식일 수 식단 생성. 중복(date,meal_type) 제거. `ingredients_text` 3000자 상한 |
| `validate_nutrition` | food_db 병렬 검색(문서당 300자 제한) + LLM 배치 1회 + 코드 레벨 수치 검증 + 완전성 검사 |
| `check_budget` | `GET /budgets` → `state.budget_info` (향후 예산 초과 차단 스캐폴딩) |
| `save_plan` | `POST /diets` + `POST /meals` asyncio.gather 병렬 저장. 실패 시 `DELETE /diets/{id}` 롤백 |

**단건 식단 그래프 (single_meal_graph)**

| 노드 | 역할 |
|------|------|
| `resolve_excluded_names` | `excluded_ingredient_ids` → `GET /ingredients`로 이름 변환 → `state.excluded_names`. ID 없으면 API 호출 생략 |
| `retrieve_single_context` | RAG: policy + guidelines 검색 (월·끼니 기반 쿼리) → `state.guidelines_context` |
| `generate_single_meal` | LLM(구조화 출력) → 밥+국+반찬 구성. 끼니별 규칙·제외 식자재·급식 인원 기반 생성. `SingleMealPlan`(menus + reason + 영양 추정치) |
| `validate_single_nutrition` | 코드 레벨 수치 검증(영양 추정치 None이면 스킵) + food_db 검색 + LLM 배치 1회 |
| `check_single_budget` | `GET /budgets?month=` → `state.budget_info` (향후 예산 초과 차단 스캐폴딩) |
| `save_single_plan` | `POST /diets` 1회 + `POST /meals` asyncio.gather 병렬 저장(메뉴 수만큼). 실패 시 diet 롤백 |

**`generate_plan` 주요 동작**
- `state["school_days"]` 기준으로 스케줄 구성 (주말·공휴일 날짜 없음)
- 7가지 다양성 규칙을 시스템 프롬프트에 포함:
  - 동일 메뉴 월 5회 이하, 같은 주 3회 이하
  - 하루 세 끼 내 단백질 주재료 중복 금지
  - 조리법 다양화, 국/탕 끼니당 1가지, 조식은 가볍게
- LLM 결과에서 `school_days` 외 날짜 필터 + (date, meal_type) 중복 제거
- `ingredients_text`: 보유 식자재 목록, 3000자 상한

**`validate_nutrition` / `validate_single_nutrition` 공통 동작**
1. 코드 레벨 수치 검증 (LLM 독립적):
   - 나트륨 > 1000mg
   - 에너지 < 200kcal (월간: MealItem 필드, 단건: SingleMealPlan 추정치. `None`이면 스킵)
   - 단백질 비율 7~20% (protein×4/kcal), 지방 비율 15~30% (fat×9/kcal)
2. 코드 통과 메뉴만 `search_food` 병렬 실행 + LLM 배치 1회 (문서당 300자 제한)
3. (월간 전용) Counter 기반 빈도 강제: 동일 메뉴 월 6회 이상 → 오류 추가
4. (월간 전용) 완전성 검사: `school_days × 3끼` 중 누락 조합 감지

### `app/agent/graph.py` — LangGraph 워크플로우

두 그래프는 구조가 동일하다. `START`에서 두 노드가 **동시 fan-out** 후 `generate_*`에서 합류  
(LangGraph StateGraph가 자동으로 배리어 조인 처리).

**공통 흐름**
```
START → [A 병렬] → generate → validate → [조건 분기]
                                         ├── retry < 3 → generate (재시도)
                                         ├── retry 소진 → END (저장 생략)
                                         └── 오류 없음 → check_budget → save → END
```

| 그래프 | 병렬 fan-out 노드 |
|--------|------------------|
| `meal_plan_graph` | `fetch_ingredients` \|\| `retrieve_context` |
| `single_meal_graph` | `resolve_excluded_names` \|\| `retrieve_single_context` |

### `app/api/agent.py` — FastAPI 라우터

**POST /agent/recommend-meal** (단건 식단 추천)
- 요청: `{ mealDate, mealType, schoolId, targetCalories?, servingCount, budgetLimit?, excludedIngredientIds[] }`
- 응답: `{ mealDate, mealType, targetCalories, servingCount, budgetLimit, menus[], reason, error }`
  - `menus[]` = 밥·국·반찬 각각 `{ name, description, ingredients[{name, quantity, unit}] }`
  - `error`: 재시도 소진 후 검증 실패 시 경고 메시지, 정상 시 null

**POST /agent/generate-plan** (월간 식단 생성)
- `_school_days(month, extra_holidays)`: 해당 월에서 주말 + 한국 공휴일(`holidays` 라이브러리) + 추가 휴무일 제외
- 요청 스키마: `{ month, school_id, holidays: [] }`  (`holidays`는 학교 재량휴업일 목록)
- 재시도 소진 후 검증 실패 잔존 시 → 200 OK + `error` 필드에 경고 메시지

---

## 4. 동작 흐름 (End-to-End)

### 4-1. 단건 식단 추천 (`POST /agent/recommend-meal`)

```
클라이언트
    │
    │  POST /agent/recommend-meal
    │  { "mealDate": "2026-07-01", "mealType": "LUNCH",
    │    "schoolId": 1, "targetCalories": 700,
    │    "servingCount": 100, "budgetLimit": 3000,
    │    "excludedIngredientIds": [3, 7] }
    │  Authorization: Bearer <JWT>
    ▼
┌────────────────────────────────────────────────────────────┐
│  FastAPI  (app/api/agent.py)                               │
│  - mealDate YYYY-MM-DD 포맷 검증                            │
│  - SingleMealState 초기화 (school_id 포함)                  │
│  - single_meal_graph.ainvoke(state) 호출                    │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────┐
│  single_meal_graph (app/agent/graph.py)                    │
│                                                            │
│  ┌─ [1] resolve_excluded_names ────────────────────────┐  │
│  │   └─ excludedIngredientIds 있을 때만 GET /ingredients│  │
│  │   └─ ID → 이름 변환 → state.excluded_names           │  │
│  │                                      (병렬 실행)      │  │
│  └─ [2] retrieve_single_context ────────────────────┐  │  │
│      └─ ChromaDB "policy" + "guidelines" 검색         │  │  │
│      └─ state.guidelines_context 업데이트             ┘  ┘  │
│                       │ (합류)                              │
│  [3] generate_single_meal                                  │
│       └─ 끼니별 구성 규칙:                                   │
│           중식/석식: 밥 1 + 국 1 + 단백질 반찬 1 + 채소 반찬 1~2│
│           조식: 죽/샌드위치/토스트 계열 (간단 구성)             │
│       └─ 제외 식자재·급식 인원·목표 칼로리 적용                 │
│       └─ with_structured_output(SingleMealPlan) 1회 호출    │
│       └─ state.result 업데이트 (menus + reason + 영양추정치)  │
│                       │                                    │
│  [4] validate_single_nutrition                             │
│       └─ 코드 레벨 검증 (영양 추정치 None이면 스킵)            │
│       └─ search_food 병렬 + LLM 배치 (문서당 300자 제한)      │
│       └─ state.validation_errors 업데이트                  │
│                       │                                    │
│         ┌─────────────┴──────────────────┐                │
│    오류 + retry<3    오류 + retry소진    오류 없음           │
│         │                │               │                 │
│   [3]재생성(최대3회) END(저장생략)   [5] check_single_budget │
│                       경고 반환          └─ GET /budgets    │
│                                               │             │
│                                     [6] save_single_plan   │
│                                       └─ POST /diets 1회   │
│                                       └─ POST /meals 병렬  │
│                                          (asyncio.gather)  │
│                                       └─ 실패 시 diet 롤백  │
└────────────────────────────────────────────────────────────┘
                       │
                       ▼
  { menus[], reason, error: null }
```

### 4-2. 월간 식단 생성 (`POST /agent/generate-plan`)

```
클라이언트 (영양사 앱)
    │
    │  POST /agent/generate-plan
    │  { "month": "2026-07", "school_id": 1, "holidays": ["2026-07-14"] }
    │  Authorization: Bearer <JWT>
    ▼
┌────────────────────────────────────────────────────────────┐
│  FastAPI  (app/api/agent.py)                               │
│  - month YYYY-MM 포맷 검증                                  │
│  - _school_days(): 주말·공휴일·재량휴업일 제외 날짜 목록 생성  │
│  - AgentState 초기화 (school_days 포함)                     │
│  - meal_plan_graph.ainvoke(state) 호출                      │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────┐
│  LangGraph 워크플로우 (app/agent/graph.py)                  │
│                                                            │
│  ┌─ [1] fetch_ingredients ──────────────────────────────┐  │
│  │   └─ GET {BACKEND_URL}/ingredients (최대 3회 재시도)  │  │
│  │   └─ state.ingredients 업데이트                       │  │
│  │                                      (병렬 실행)      │  │
│  └─ [2] retrieve_context ───────────────────────────┐   │  │
│      └─ ChromaDB "policy" 검색 (영양기준)            │   │  │
│      └─ ChromaDB "guidelines" 검색 (식단가이드)      │   │  │
│      └─ state.guidelines_context 업데이트            ┘   ┘  │
│                       │ (합류)                              │
│  [3] generate_plan    ┘     (오류 있으면 → END)             │
│       └─ school_days 기준 스케줄 구성                        │
│       └─ 7가지 다양성 규칙 포함 시스템 프롬프트               │
│       └─ ingredients_text 3000자 상한                       │
│       └─ claude-sonnet-4-6 with_structured_output           │
│       └─ school_days 외 날짜 필터 + (date,meal_type) 중복 제거│
│       └─ state.meal_plan 업데이트                           │
│                       │                                    │
│  [4] validate_nutrition                                    │
│       └─ 전체 메뉴 search_food 병렬 실행 (asyncio.gather)   │
│       └─ LLM 배치 1회 호출 (문서당 300자 제한)               │
│       └─ Counter로 월 6회 이상 메뉴 감지                    │
│       └─ 코드 레벨 수치 검증 (나트륨/kcal/단백질/지방)        │
│       └─ 완전성 검사 (school_days × 3끼 누락 감지)           │
│       └─ state.validation_errors 업데이트                  │
│                       │                                    │
│         ┌─────────────┴────────────────────┐              │
│    오류 + retry<3    오류 + retry소진       오류 없음        │
│         │                │                  │              │
│   [3]재생성(최대3회)  END(저장생략)      [5] check_budget    │
│                       경고 반환              └─ GET /budgets │
│                                              └─ state.budget_info
│                                                   │        │
│                                            [6] save_plan   │
│                                              └─ 병렬 저장:  │
│                                                 POST /diets │
│                                                 POST /meals │
│                                              └─ 실패 시:    │
│                                                 DELETE /diets/{id}
│                                                 (롤백)      │
└────────────────────────────────────────────────────────────┘
                       │
                       ▼
  { month, total_meals, meal_plan[], validation_errors[], budget_info, error }
```

---

## 5. RAG 3개 컬렉션 역할 분리

| 컬렉션 | 사용 노드 | 검색 방식 | 용도 |
|--------|----------|-----------|------|
| `policy` | `retrieve_context`, `retrieve_single_context` | 벡터 검색 | 영양 기준량, 급식 정책 |
| `guidelines` | `retrieve_context`, `retrieve_single_context` | 벡터 검색 | 식단 작성 가이드라인 |
| `food_db` | `validate_nutrition`, `validate_single_nutrition` | BM25+벡터 병렬 하이브리드(RRF k=60) | 개별 식품 영양 성분 조회 |

`policy`와 `guidelines`는 식단 **생성 전** 기준 컨텍스트 (월간·단건 공통),  
`food_db`는 생성 **후** 각 메뉴의 영양소 검증에 사용 (월간·단건 공통).

---

## 6. 로컬 테스트 방법

```bash
# 터미널 1: Mock 백엔드 서버 실행 (실제 백엔드 없이 테스트)
uv run uvicorn test.mock_backend:app --host 0.0.0.0 --port 8080

# 터미널 2: AI 서버 실행
uv run uvicorn app.main:app --reload --port 8000

# 터미널 3: CLI 테스트 (대화형)
uv run python test/cli.py
# → test/result/meal_plan_YYYY-MM.json 에 결과 저장

# Swagger UI
# http://localhost:8000/docs
```

**Mock 백엔드 제공 엔드포인트**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/ingredients` | 더미 식자재 21종 반환 |
| GET | `/budgets?month=` | 더미 예산 정보 반환 |
| POST | `/diets` | 식단 생성 (인메모리 저장, id 반환) |
| POST | `/meals` | 메뉴 생성 (인메모리 저장) |
| DELETE | `/diets/{id}` | 식단 삭제 (연관 meals cascade, 롤백용). 존재하지 않는 ID → 404 |

---

## 7. 배포 시 주의사항

- **RAG 인덱싱**: 서버에 원본 데이터 파일(PDF 2개 + Excel 1개)을 `./data/`에 올린 후 `uv run python -m app.rag.ingest` 1회 실행
- **ChromaDB 경로**: `CHROMA_DB_PATH`를 절대경로로 설정 권장 (예: `/opt/hololog-ai/chroma_db`)
- **DELETE /diets/{id}**: `save_plan` / `save_single_plan` 롤백에 필요. 실제 백엔드에도 cascade 삭제 엔드포인트 필요
- **임베딩 모델**: 첫 실행 시 `BAAI/bge-m3` 자동 다운로드 (~1.5GB). 인터넷 연결 및 디스크 공간 확인 필요

---

## 8. LangSmith 추적

`config.py` import 시 `LANGCHAIN_TRACING_V2=true` 자동 설정.  
모든 LangChain/LangGraph 호출이 LangSmith 대시보드에서 추적된다.

- 추적 대상: `generate_plan` / `generate_single_meal` (LLM), `validate_nutrition` / `validate_single_nutrition` (LLM 배치 1회)
- 프로젝트명: `hololog-ai` (`.env`의 `LANGCHAIN_PROJECT`로 변경 가능)

---

## 9. 주요 의존성

| 패키지 | 버전 | 역할 |
|--------|------|------|
| `fastapi` | 0.136 | API 서버 |
| `langgraph` | 1.2 | 에이전트 워크플로우 상태 머신 |
| `langchain` | 1.3 | LLM/임베딩 추상화 (`init_chat_model`) |
| `langchain-anthropic` | — | claude-sonnet-4-6 호출, 구조화 출력 |
| `langchain-experimental` | 0.4 | SemanticChunker (의미 기반 PDF 청킹) |
| `langchain-huggingface` | 1.2 | BAAI/bge-m3 로컬 임베딩 |
| `langsmith` | 0.8 | LLM 호출 추적/모니터링 |
| `chromadb` | 1.5 | 로컬 벡터 데이터베이스 |
| `rank-bm25` | 0.2 | food_db BM25 하이브리드 검색 |
| `pymupdf` | 1.27 | PDF 텍스트 추출 |
| `pandas` | 3.0 | Excel 음식DB 처리 |
| `httpx` | 0.28 | 백엔드 API 비동기 HTTP 클라이언트 |
| `holidays` | 0.99 | 한국 공휴일 자동 감지 |
