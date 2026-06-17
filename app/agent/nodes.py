"""
LangGraph 노드 함수 모음.
각 노드는 AgentState를 받아 업데이트할 필드만 dict로 반환.
"""
from __future__ import annotations

import asyncio

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agent.state import AgentState
from app.core.client import backend_client
from app.core.config import settings
from app.rag.retriever import search_food, search_joined

# ── 상수 ──────────────────────────────────────────────────────────────────────

_VALIDATE_SEM = asyncio.Semaphore(5)

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


class NutritionVerdict(BaseModel):
    passed: bool
    issue: str = ""


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
    """RAG: policy + guidelines 컬렉션에서 급식 기준 검색 (병렬)."""
    month_num = int(state["month"].split("-")[1])
    nutrition_query = "학교급식 영양기준 에너지 단백질 지방 나트륨 칼슘"
    planning_query = f"{month_num}월 학교급식 식단작성 메뉴 다양성 계절"
    policy, guidelines = await asyncio.gather(
        asyncio.to_thread(search_joined, "policy", nutrition_query, 5),
        asyncio.to_thread(search_joined, "guidelines", planning_query, 5),
    )
    context = f"[급식 정책 — 영양기준]\n{policy}\n\n[식단 작성 가이드라인]\n{guidelines}"
    return {"guidelines_context": context}


_MEAL_TYPES = ["BREAKFAST", "LUNCH", "DINNER"]


async def generate_plan(state: AgentState) -> dict:
    """LLM으로 월간 식단 초안 생성. 재시도 시 이전 오류 컨텍스트 포함."""
    if state.get("error"):
        return {}

    school_days = state["school_days"]
    total_meals = len(school_days) * len(_MEAL_TYPES)

    ingredients_text = "\n".join(
        f"- {item.get('name', '?')} {item.get('quantity', '?')}{item.get('unit', '')}"
        for item in state["ingredients"]
    ) or "정보 없음"

    schedule = "\n".join(
        f"{day}: {', '.join(_MEAL_TYPES)}"
        for day in school_days
    )

    error_section = ""
    if state["validation_errors"]:
        error_lines = "\n".join(
            f"- {e.get('date')} {e.get('meal_type')}: {e.get('issue')}"
            for e in state["validation_errors"]
        )
        error_section = f"\n\n[이전 시도 문제점 — 반드시 개선]\n{error_lines}"

    system = SystemMessage(content=(
        "당신은 학교급식 월간 식단 계획 전문가입니다.\n"
        "아래 규칙을 엄격히 따라 JSON 형식으로 작성하세요.\n\n"
        "【필수 규칙】\n"
        "1. 제공된 급식 일정의 모든 날짜에 조식(BREAKFAST)·중식(LUNCH)·석식(DINNER) 세 끼를 빠짐없이 작성합니다.\n"
        "2. 일정에 없는 날(주말·공휴일)에는 절대 식단을 작성하지 않습니다.\n\n"
        "【다양성 규칙】\n"
        "3. 동일 메뉴는 한 달에 최대 1회만 등장합니다.\n"
        "4. 단백질 주재료(돼지고기·닭고기·소고기·생선·두부·계란 등)가 하루 세 끼 내에서 중복되지 않도록 합니다.\n"
        "5. 조리법(볶음·찜·국·구이·조림·무침·튀김·전 등)을 매일 다양하게 조합합니다.\n"
        "6. 국/탕/찌개류는 각 끼니별 최대 한 가지만 포함합니다.\n"
        "7. 조식은 가볍게(죽·샌드위치·토스트·미음 계열), 중식·석식은 밥+국+반찬 구성을 권장합니다.\n\n"
        "한국 학교 급식에 적합한 메뉴를 선택하세요."
    ))
    human = HumanMessage(content=(
        f"대상 월: {state['month']}\n"
        f"급식 일정 ({len(school_days)}일 × 3끼 = {total_meals}개 메뉴):\n{schedule}\n\n"
        f"[영양 기준 및 가이드라인]\n{state['guidelines_context']}\n\n"
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


async def _check_meal(meal: dict) -> dict | None:
    async with _VALIDATE_SEM:
        menu = meal.get("menu_name", "")
        docs = await asyncio.to_thread(search_food, menu, 3)
        check_prompt = (
            f"다음 메뉴의 영양 정보를 참고하여 학교급식 영양 기준(에너지 1/3, "
            f"단백질 7~20%, 지방 15~30%, 나트륨 1000mg 이하)을 충족하는지 판단하세요.\n\n"
            f"메뉴: {menu}\n"
            f"추정 영양정보 (DB 참고):\n{docs}\n\n"
            f"식단 추정값: kcal={meal.get('estimated_kcal')}, "
            f"단백질={meal.get('estimated_protein_g')}g, "
            f"지방={meal.get('estimated_fat_g')}g, "
            f"나트륨={meal.get('estimated_sodium_mg')}mg"
        )
        structured = _get_llm().with_structured_output(NutritionVerdict)
        result: NutritionVerdict = await structured.ainvoke([HumanMessage(content=check_prompt)])
        if not result.passed:
            return {
                "date": meal.get("date"),
                "meal_type": meal.get("meal_type"),
                "menu": menu,
                "issue": result.issue,
            }
        return None


async def validate_nutrition(state: AgentState) -> dict:
    """RAG food_db로 각 메뉴 영양소 추정 → 기준 미달 항목 수집 (병렬)."""
    results = await asyncio.gather(*[_check_meal(m) for m in state["meal_plan"]])
    errors = [r for r in results if r is not None]
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


async def _save_meal(client, meal: dict, school_id: int) -> None:
    diet_resp = await client.post("/diets", json={
        "date": meal["date"],
        "meal_type": meal["meal_type"],
        "school_id": school_id,
    })
    diet_resp.raise_for_status()
    diet_id = diet_resp.json().get("id")
    meal_resp = await client.post("/meals", json={
        "diet_id": diet_id,
        "menu_name": meal["menu_name"],
        "kcal": meal["estimated_kcal"],
        "protein": meal["estimated_protein_g"],
        "fat": meal["estimated_fat_g"],
        "sodium": meal["estimated_sodium_mg"],
    })
    meal_resp.raise_for_status()


async def save_plan(state: AgentState) -> dict:
    """생성된 식단을 /diets + /meals API로 저장 (병렬)."""
    async with backend_client(state["auth_token"]) as client:
        results = await asyncio.gather(
            *[_save_meal(client, meal, state["school_id"]) for meal in state["meal_plan"]],
            return_exceptions=True,
        )
    errors = [
        f"{meal.get('date')} {meal.get('meal_type')}: {r}"
        for meal, r in zip(state["meal_plan"], results)
        if isinstance(r, Exception)
    ]
    if errors:
        return {"error": f"일부 저장 실패: {'; '.join(errors[:3])}"}
    return {"error": None}
