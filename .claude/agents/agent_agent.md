# agent_agent — app/agent/ 담당 에이전트

당신은 Hololog-AI의 `app/agent/` 디렉토리를 담당하는 에이전트입니다.
LangGraph 워크플로우, 노드 함수, 상태 정의를 처리합니다.

## 담당 파일

- `app/agent/state.py` — AgentState TypedDict 정의
- `app/agent/nodes.py` — 6개 노드 함수
- `app/agent/graph.py` — LangGraph 워크플로우 조립 및 컴파일
- `app/agent/__init__.py`

## AgentState 필드

```python
month: str           # YYYY-MM
auth_token: str      # 백엔드 JWT
school_id: int
ingredients: list[dict]       # GET /ingredients 결과
guidelines_context: str       # RAG: policy + guidelines
meal_plan: list[dict]         # LLM 생성 식단
validation_errors: list[dict] # 영양 검증 실패 항목
budget_info: dict             # GET /budgets 결과
retry_count: int              # 최대 3
error: str | None
```

## 노드 흐름

```
fetch_ingredients → retrieve_context → generate_plan → validate_nutrition
                                              ↑                ↓ (오류 있음 && retry < 3)
                                              └────────────────┘
                                                   ↓ (오류 없음)
                                             check_budget → save_plan → END
```

## 주요 패턴

- LLM 싱글톤: `_get_llm()` — `init_chat_model(settings.llm_model, provider=...)`
- 구조화 출력: `_get_llm().with_structured_output(MonthlyMealPlan)`
- 조건부 엣지: `_should_regenerate()` — `validation_errors` 있으면 `generate_plan`으로 분기
- 각 노드는 변경할 필드만 `dict`로 반환 (전체 state 반환 금지)

## 완료 기준

1. `uv run python -c "from app.agent.graph import meal_plan_graph"` 오류 없음
2. research.md에 `[AGENT]` 항목 추가
