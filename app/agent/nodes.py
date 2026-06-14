"""
LangGraph 노드 함수 모음.
각 노드는 AgentState를 받아 업데이트할 필드만 dict로 반환.
"""
from __future__ import annotations

import calendar
from datetime import date

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agent.state import AgentState
from app.core.client import backend_client
from app.core.config import settings
from app.rag.retriever import search_joined

# ── LLM (싱글톤) ──────────────────────────────────────────────────────────────

_llm: BaseChatModel | None = None


def _get_llm() -> BaseChatModel:
    global _llm
    if _llm is None:
        _llm = init_chat_model(
            settings.llm_model,
            model_provider=settings.llm_provider,
            temperature=0.3,
        )
    return _llm


# ── Pydantic 출력 스키마 ───────────────────────────────────────────────────────

class MealItem(BaseModel):
    date: str           # YYYY-MM-DD
    meal_type: str      # BREAKFAST | LUNCH | DINNER
    menu_name: str
    ingredients_used: list[str]
    estimated_kcal: float
    estimated_protein_g: float
    estimated_fat_g: float
    estimated_sodium_mg: float


class MonthlyMealPlan(BaseModel):
    meals: list[MealItem]


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _weekdays_in_month(year: int, month: int) -> list[str]:
    """해당 월의 주중(월~금) 날짜 목록 반환."""
    _, last_day = calendar.monthrange(year, month)
    return [
        date(year, month, d).isoformat()
        for d in range(1, last_day + 1)
        if date(year, month, d).weekday() < 5
    ]


# ── 노드 함수 ──────────────────────────────────────────────────────────────────

async def fetch_ingredients(state: AgentState) -> dict:
    """GET /ingredients 로 보유 식자재 조회."""
    try:
        async with backend_client(state["auth_token"]) as client:
            resp = await client.get("/ingredients")
            resp.raise_for_status()
            return {"ingredients": resp.json(), "error": None}
    except Exception as e:
        return {"ingredients": [], "error": f"식자재 조회 실패: {e}"}


async def retrieve_context(state: AgentState) -> dict:
    """RAG: policy + guidelines 컬렉션에서 급식 기준 검색."""
    query = f"{state['month']} 학교급식 영양 기준 식단 작성"
    policy = search_joined("policy", query, n_results=5)
    guidelines = search_joined("guidelines", query, n_results=5)
    context = f"[급식 정책]\n{policy}\n\n[식단 작성 가이드라인]\n{guidelines}"
    return {"guidelines_context": context}


async def generate_plan(state: AgentState) -> dict:
    """LLM으로 월간 식단 초안 생성. 재시도 시 이전 오류 컨텍스트 포함."""
    year, month = map(int, state["month"].split("-"))
    school_days = _weekdays_in_month(year, month)
    ingredients_text = "\n".join(
        f"- {item.get('name', '?')} {item.get('quantity', '?')}{item.get('unit', '')}"
        for item in state["ingredients"]
    ) or "정보 없음"

    error_section = ""
    if state["validation_errors"]:
        error_lines = "\n".join(
            f"- {e.get('date')} {e.get('meal_type')}: {e.get('issue')}"
            for e in state["validation_errors"]
        )
        error_section = f"\n\n[이전 시도 문제점 — 반드시 개선]\n{error_lines}"

    system = SystemMessage(content=(
        "당신은 학교급식 월간 식단 계획 전문가입니다. "
        "주어진 식자재와 영양 기준에 맞는 한 달 치 식단을 JSON으로 작성하세요. "
        "한국 학교 급식에 적합한 메뉴를 선택하고, 같은 메뉴가 주 2회 이상 반복되지 않도록 하세요."
    ))
    human = HumanMessage(content=(
        f"대상 월: {state['month']}\n"
        f"급식 일자: {', '.join(school_days)}\n\n"
        f"[영양 기준]\n{state['guidelines_context']}\n\n"
        f"[보유 식자재]\n{ingredients_text}"
        f"{error_section}"
    ))

    structured = _get_llm().with_structured_output(MonthlyMealPlan)
    result: MonthlyMealPlan = await structured.ainvoke([system, human])

    return {
        "meal_plan": [m.model_dump() for m in result.meals],
        "retry_count": state["retry_count"] + (1 if state["validation_errors"] else 0),
        "validation_errors": [],
    }


async def validate_nutrition(state: AgentState) -> dict:
    """RAG food_db로 각 메뉴 영양소 추정 → 기준 미달 항목 수집."""
    errors: list[dict] = []

    for meal in state["meal_plan"]:
        menu = meal.get("menu_name", "")
        docs = search_joined("food_db", menu, n_results=3)

        # LLM에게 영양 검증 판단 위임 (소형 판단)
        check_prompt = (
            f"다음 메뉴의 영양 정보를 참고하여 학교급식 영양 기준(에너지 1/3, "
            f"단백질 7~20%, 지방 15~30%, 나트륨 1000mg 이하)을 충족하는지 판단하세요.\n\n"
            f"메뉴: {menu}\n"
            f"추정 영양정보 (DB 참고):\n{docs}\n\n"
            f"식단 추정값: kcal={meal.get('estimated_kcal')}, "
            f"단백질={meal.get('estimated_protein_g')}g, "
            f"지방={meal.get('estimated_fat_g')}g, "
            f"나트륨={meal.get('estimated_sodium_mg')}mg\n\n"
            "기준 미달이면 'FAIL: <이유>', 충족이면 'PASS'로만 답하세요."
        )

        resp = await _get_llm().ainvoke([HumanMessage(content=check_prompt)])
        verdict = resp.content.strip()

        if verdict.startswith("FAIL"):
            errors.append({
                "date": meal.get("date"),
                "meal_type": meal.get("meal_type"),
                "menu": menu,
                "issue": verdict.replace("FAIL:", "").strip(),
            })

    return {"validation_errors": errors}


async def check_budget(state: AgentState) -> dict:
    """GET /budgets 로 예산 잔액 확인."""
    try:
        async with backend_client(state["auth_token"]) as client:
            resp = await client.get(f"/budgets?month={state['month']}")
            resp.raise_for_status()
            return {"budget_info": resp.json()}
    except Exception as e:
        # 예산 API 실패는 치명적 오류로 처리하지 않고 경고로 기록
        return {"budget_info": {"warning": f"예산 조회 실패: {e}"}}


async def save_plan(state: AgentState) -> dict:
    """생성된 식단을 /diets + /meals API로 저장."""
    saved: list[dict] = []
    errors: list[str] = []

    async with backend_client(state["auth_token"]) as client:
        for meal in state["meal_plan"]:
            try:
                # 1. 식단 생성
                diet_resp = await client.post("/diets", json={
                    "date": meal["date"],
                    "meal_type": meal["meal_type"],
                    "school_id": state["school_id"],
                })
                diet_resp.raise_for_status()
                diet_id = diet_resp.json().get("id")

                # 2. 메뉴 저장
                meal_resp = await client.post("/meals", json={
                    "diet_id": diet_id,
                    "menu_name": meal["menu_name"],
                    "kcal": meal["estimated_kcal"],
                    "protein": meal["estimated_protein_g"],
                    "fat": meal["estimated_fat_g"],
                    "sodium": meal["estimated_sodium_mg"],
                })
                meal_resp.raise_for_status()
                saved.append({"diet_id": diet_id, "menu": meal["menu_name"]})
            except Exception as e:
                errors.append(f"{meal.get('date')} {meal.get('meal_type')}: {e}")

    if errors:
        return {"error": f"일부 저장 실패: {'; '.join(errors[:3])}"}
    return {"error": None}
