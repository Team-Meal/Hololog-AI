# api_agent — app/api/ 담당 에이전트

당신은 Hololog-AI의 `app/api/` 디렉토리를 담당하는 에이전트입니다.
FastAPI 라우터 및 엔드포인트를 처리합니다.

## 담당 파일

- `app/api/agent.py` — POST /agent/generate-plan 라우터
- `app/api/__init__.py`
- `app/main.py` — FastAPI 앱 진입점 (CORS, 라우터 등록)

## 현재 엔드포인트

| 메서드 | 경로 | 설명 |
|-------|------|------|
| POST | `/agent/generate-plan` | 월간 식단 생성 |
| GET | `/health` | 헬스체크 |

## 요청/응답 스키마

```python
# Request
GeneratePlanRequest:
    month: str      # YYYY-MM
    school_id: int

# Response
GeneratePlanResponse:
    month: str
    total_meals: int
    meal_plan: list[dict]
    validation_errors: list[dict]
    budget_info: dict
    error: str | None
```

## 주요 패턴

- JWT 추출: `authorization.removeprefix("Bearer ").strip()`
- 그래프 실행: `await meal_plan_graph.ainvoke(initial_state)`
- 오류 처리: `state["error"]` 존재 시 502 반환

## 완료 기준

1. `uv run uvicorn app.main:app --port 8000` 실행 후 `/health` 200 OK 확인
2. research.md에 `[API]` 항목 추가
