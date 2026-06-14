from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.agent.graph import meal_plan_graph
from app.agent.state import AgentState

router = APIRouter(prefix="/agent", tags=["agent"])


class GeneratePlanRequest(BaseModel):
    month: str      # YYYY-MM
    school_id: int


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

    return GeneratePlanResponse(
        month=body.month,
        total_meals=len(final_state["meal_plan"]),
        meal_plan=final_state["meal_plan"],
        validation_errors=final_state["validation_errors"],
        budget_info=final_state["budget_info"],
        error=None,
    )
