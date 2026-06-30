from typing import TypedDict


class AgentState(TypedDict):
    month: str          # YYYY-MM
    auth_token: str     # 백엔드 API 인증용
    school_id: int
    school_days: list[str]          # 급식 제공 날짜 (주말·공휴일 제외, YYYY-MM-DD)

    ingredients: list[dict]         # GET /ingredients 결과
    guidelines_context: str         # RAG: policy + guidelines 검색 결과
    meal_plan: list[dict]           # LLM이 생성한 식단 초안
    validation_errors: list[dict]   # 영양 검증 실패 항목
    budget_info: dict               # GET /budgets 결과
    retry_count: int                # 재생성 횟수 (최대 3)
    error: str | None               # 치명적 오류 메시지
    scored_ingredients: list[dict]  # 룰 스코어링 결과 (ScoredIngredient.__dict__)
    meal_metrics: dict              # 4.2 지표 5개


class SingleMealState(TypedDict):
    meal_date: str          # YYYY-MM-DD
    meal_type: str          # BREAKFAST | LUNCH | DINNER
    auth_token: str
    school_id: int
    target_calories: int | None
    serving_count: int
    budget_limit: int | None
    excluded_ingredient_ids: list[int]   # 원본 ID 목록
    excluded_names: list[str]            # ID → 이름 변환 결과
    guidelines_context: str
    result: dict | None     # generate_single_meal 결과
    validation_errors: list[dict]
    retry_count: int
    budget_info: dict
    error: str | None
    scored_ingredients: list[dict]  # 룰 스코어링 결과
    qa_pairs: list[dict]            # 7.4 예상 Q&A 6개 [{question, answer}]
    meal_metrics: dict              # 4.2 지표 5개
