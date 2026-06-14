from typing import TypedDict


class AgentState(TypedDict):
    month: str          # YYYY-MM
    auth_token: str     # 백엔드 API 인증용
    school_id: int

    ingredients: list[dict]         # GET /ingredients 결과
    guidelines_context: str         # RAG: policy + guidelines 검색 결과
    meal_plan: list[dict]           # LLM이 생성한 식단 초안
    validation_errors: list[dict]   # 영양 검증 실패 항목
    budget_info: dict               # GET /budgets 결과
    retry_count: int                # 재생성 횟수 (최대 3)
    error: str | None               # 치명적 오류 메시지
