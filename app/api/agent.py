import calendar
import re
from datetime import date as _date

import holidays as _holidays_lib
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, field_validator

from app.agent.graph import meal_plan_graph
from app.agent.state import AgentState

router = APIRouter(prefix="/agent", tags=["agent"])


def _school_days(month: str, extra_holidays: list[str]) -> list[str]:
    """주말·한국 공휴일·추가 휴무일을 제외한 급식 제공 날짜 목록."""
    year, m = map(int, month.split("-"))
    _, last_day = calendar.monthrange(year, m)

    kr_holidays = _holidays_lib.country_holidays("KR", years=year)
    holiday_set = {d.isoformat() for d in kr_holidays} | set(extra_holidays)

    return [
        _date(year, m, d).isoformat()
        for d in range(1, last_day + 1)
        if _date(year, m, d).weekday() < 5
        and _date(year, m, d).isoformat() not in holiday_set
    ]


class GeneratePlanRequest(BaseModel):
    month: str          # YYYY-MM
    school_id: int
    holidays: list[str] = []    # 학교 재량휴업일 등 추가 휴무일 (YYYY-MM-DD)

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v):
            raise ValueError("month must be YYYY-MM format (e.g. 2026-07)")
        return v


class GeneratePlanResponse(BaseModel):
    month: str
    total_meals: int
    meal_plan: list[dict]
    validation_errors: list[dict]
    budget_info: dict
    error: str | None


@router.post("/generate-plan", response_model=GeneratePlanResponse)
async def generate_plan(
    body: GeneratePlanRequest,
    authorization: str = Header(...),
) -> GeneratePlanResponse:
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 토큰 없음")

    initial_state: AgentState = {
        "month": body.month,
        "auth_token": token,
        "school_id": body.school_id,
        "school_days": _school_days(body.month, body.holidays),
        "ingredients": [],
        "guidelines_context": "",
        "meal_plan": [],
        "validation_errors": [],
        "budget_info": {},
        "retry_count": 0,
        "error": None,
    }

    final_state: AgentState = await meal_plan_graph.ainvoke(initial_state)

    if final_state.get("error"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=final_state["error"],
        )

    # 재시도 소진 후 검증 실패가 남아있으면 저장 생략됨 (budget_info 없음)
    warn: str | None = None
    if final_state.get("validation_errors") and not final_state.get("budget_info"):
        n = len(final_state["validation_errors"])
        warn = f"영양 검증 실패 {n}건으로 저장 생략됨"

    return GeneratePlanResponse(
        month=body.month,
        total_meals=len(final_state["meal_plan"]),
        meal_plan=final_state["meal_plan"],
        validation_errors=final_state["validation_errors"],
        budget_info=final_state.get("budget_info", {}),
        error=warn,
    )
