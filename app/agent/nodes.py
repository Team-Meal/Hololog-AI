"""
LangGraph 노드 함수 모음.
각 노드는 AgentState를 받아 업데이트할 필드만 dict로 반환.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agent.state import AgentState, SingleMealState
from app.core.client import backend_client
from app.core.config import settings
from app.rag.retriever import search_food, search_joined

# ── LLM (싱글톤) ──────────────────────────────────────────────────────────────

_llm: BaseChatModel | None = None


def _get_llm() -> BaseChatModel:
    global _llm
    if _llm is None:
        _llm = init_chat_model(
            settings.llm_model,
            model_provider=settings.llm_provider,
            temperature=0.3,
            max_retries=settings.llm_max_retries,
        )
    return _llm


# ── Pydantic 출력 스키마 ───────────────────────────────────────────────────────

class MealItem(BaseModel):
    date: str           # YYYY-MM-DD
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER"]
    menu_name: str
    ingredients_used: list[str]
    estimated_kcal: float
    estimated_protein_g: float
    estimated_fat_g: float
    estimated_sodium_mg: float


class MonthlyMealPlan(BaseModel):
    meals: list[MealItem]


# ── 단건 식단 스키마 ───────────────────────────────────────────────────────────

class MenuIngredient(BaseModel):
    name: str
    quantity: int
    unit: str  # G | KG | ML | L | EA | BOX | PACK | BUNDLE | BAG | CAN | BOTTLE


class MenuItem(BaseModel):
    name: str
    description: str
    ingredients: list[MenuIngredient]


class SingleMealPlan(BaseModel):
    menus: list[MenuItem]   # 밥 1 + 국 1 + 반찬 2~3
    reason: str
    estimated_kcal: float | None = None        # 1인분 기준 총 칼로리 (내부 검증용)
    estimated_protein_g: float | None = None
    estimated_fat_g: float | None = None
    estimated_sodium_mg: float | None = None


class MealVerdict(BaseModel):
    date: str
    meal_type: str
    menu_name: str
    passed: bool
    issue: str = ""


class BatchNutritionVerdict(BaseModel):
    verdicts: list[MealVerdict]


# ── 노드 함수 ──────────────────────────────────────────────────────────────────

async def fetch_ingredients(state: AgentState) -> dict:
    """GET /ingredients 로 보유 식자재 조회. 일시적 오류 시 최대 3회 재시도."""
    for attempt in range(3):
        try:
            async with backend_client(state["auth_token"]) as client:
                resp = await client.get("/ingredients")
                resp.raise_for_status()
                return {"ingredients": resp.json(), "error": None}
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1)
            else:
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
    context = (
        f"[급식 정책 — 영양기준]\n{policy[:_MAX_RAG_CHARS]}\n\n"
        f"[식단 작성 가이드라인]\n{guidelines[:_MAX_RAG_CHARS]}"
    )
    return {"guidelines_context": context}


_MEAL_TYPES = ["BREAKFAST", "LUNCH", "DINNER"]
_MAX_RAG_CHARS = 3000  # policy/guidelines 각각 최대 3000자 — 토큰 비용 상한


async def generate_plan(state: AgentState) -> dict:
    """LLM으로 월간 식단 초안 생성. 재시도 시 이전 오류 컨텍스트 포함."""
    if state.get("error"):
        return {}

    school_days = state["school_days"]
    total_meals = len(school_days) * len(_MEAL_TYPES)

    ingredients_text = (
        "\n".join(
            f"- {item.get('name', '?')} {item.get('quantity', '?')}{item.get('unit', '')}"
            for item in state["ingredients"]
        )[:3000]
        or "정보 없음"
    )

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
        "3. 동일 메뉴는 한 달 전체에서 5회를 초과하지 않으며, 같은 주(월~금)에 3회 이상 등장하지 않습니다.\n"
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

    school_day_set = set(school_days)
    filtered = [m for m in result.meals if m.date in school_day_set]

    # (date, meal_type) 중복 제거 — first-wins
    seen: set[tuple[str, str]] = set()
    deduped: list[MealItem] = []
    for m in filtered:
        key = (m.date, m.meal_type)
        if key not in seen:
            seen.add(key)
            deduped.append(m)

    return {
        "meal_plan": [m.model_dump() for m in deduped],
        "retry_count": state["retry_count"] + (1 if state["validation_errors"] else 0),
        "validation_errors": [],
    }


async def validate_nutrition(state: AgentState) -> dict:
    """영양 검증 — 코드 검사 선행 후 통과 메뉴만 LLM 배치 1회 호출."""
    meals = state["meal_plan"]
    if not meals:
        return {"validation_errors": []}

    errors: list[dict] = []

    # 1. 빈도 강제: 월 6회 이상 등장 → 재시도 유발
    menu_counts = Counter(m.get("menu_name", "") for m in meals)
    for name, cnt in menu_counts.items():
        if cnt >= 6:
            errors.append({
                "date": "-", "meal_type": "-", "menu": name,
                "issue": f"월 {cnt}회 등장 — 5회 이하로 줄이세요",
            })

    # 2. 코드 레벨 수치 검증 (LLM 호출 전 선행 — 명확한 위반만 확정 처리)
    code_failed_keys: set[tuple[str, str]] = set()
    for m in meals:
        issues: list[str] = []
        sodium = m.get("estimated_sodium_mg") or 0
        kcal = m.get("estimated_kcal") or 0
        protein = m.get("estimated_protein_g") or 0
        fat = m.get("estimated_fat_g") or 0
        if sodium > 1000:
            issues.append(f"나트륨 {sodium:.0f}mg 초과(기준 1000mg)")
        if kcal < 200:
            issues.append(f"에너지 {kcal:.0f}kcal 부족")
        if kcal > 0:
            if not (0.07 <= protein * 4 / kcal <= 0.20):
                issues.append(f"단백질 비율 {protein * 4 / kcal:.0%}(기준 7~20%)")
            if not (0.15 <= fat * 9 / kcal <= 0.30):
                issues.append(f"지방 비율 {fat * 9 / kcal:.0%}(기준 15~30%)")
        if issues:
            key = (m.get("date", ""), m.get("meal_type", ""))
            code_failed_keys.add(key)
            errors.append({
                "date": m.get("date", ""), "meal_type": m.get("meal_type", ""),
                "menu": m.get("menu_name", ""), "issue": " / ".join(issues),
            })

    # 3. 코드 통과 메뉴만 LLM으로 전송 (search_food n_results=1, 추정 수치 제외)
    llm_meals = [
        m for m in meals
        if (m.get("date", ""), m.get("meal_type", "")) not in code_failed_keys
    ]
    if llm_meals:
        docs_list = await asyncio.gather(*[
            asyncio.to_thread(search_food, m.get("menu_name", ""), 1)
            for m in llm_meals
        ])
        lines = [
            f"{i + 1}. {m['date']} [{m['meal_type']}] {m['menu_name']}\n"
            f"   영양DB: {(docs or '정보없음')[:300]}"
            for i, (m, docs) in enumerate(zip(llm_meals, docs_list))
        ]
        prompt = (
            "각 메뉴가 학교급식 영양 기준(에너지 1/3, 단백질 7~20%, 지방 15~30%, 나트륨 1000mg 이하)을 "
            "충족하는지 판단하고 date·meal_type·menu_name·passed·issue를 반환하세요.\n\n"
            + "\n\n".join(lines)
        )
        structured = _get_llm().with_structured_output(BatchNutritionVerdict)
        result: BatchNutritionVerdict = await structured.ainvoke([HumanMessage(content=prompt)])
        errors += [
            {"date": v.date, "meal_type": v.meal_type, "menu": v.menu_name, "issue": v.issue}
            for v in result.verdicts if not v.passed
        ]

    # 4. 완전성 검사: 급식일 × 3끼 누락 감지
    school_days_list = state.get("school_days", [])
    if school_days_list:
        expected = {(d, mt) for d in school_days_list for mt in _MEAL_TYPES}
        actual = {(m.get("date"), m.get("meal_type")) for m in meals}
        for day, mt in sorted(expected - actual):
            errors.append({"date": day, "meal_type": mt, "menu": "-", "issue": "식단 누락"})

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


async def _save_meal(client, meal: dict, school_id: int) -> str:
    diet_resp = await client.post("/diets", json={
        "date": meal["date"],
        "meal_type": meal["meal_type"],
        "school_id": school_id,
    })
    diet_resp.raise_for_status()
    diet_id = diet_resp.json().get("id")
    if diet_id is None:
        raise ValueError("backend /diets response missing 'id' field")
    meal_resp = await client.post("/meals", json={
        "diet_id": diet_id,
        "menu_name": meal["menu_name"],
        "kcal": meal["estimated_kcal"],
        "protein": meal["estimated_protein_g"],
        "fat": meal["estimated_fat_g"],
        "sodium": meal["estimated_sodium_mg"],
    })
    meal_resp.raise_for_status()
    return str(diet_id)


async def save_plan(state: AgentState) -> dict:
    """생성된 식단을 /diets + /meals API로 저장 (병렬). 실패 시 성공 건 롤백."""
    async with backend_client(state["auth_token"]) as client:
        results = await asyncio.gather(
            *[_save_meal(client, meal, state["school_id"]) for meal in state["meal_plan"]],
            return_exceptions=True,
        )
        saved_ids = [r for r in results if not isinstance(r, Exception)]
        errors = [
            f"{meal.get('date')} {meal.get('meal_type')}: {r}"
            for meal, r in zip(state["meal_plan"], results)
            if isinstance(r, Exception)
        ]
        if errors:
            for diet_id in saved_ids:
                try:
                    await client.delete(f"/diets/{diet_id}")
                except Exception:
                    pass
            return {"error": f"저장 실패 {len(errors)}건, 롤백 완료: {'; '.join(errors[:3])}"}
    return {"error": None}


# ── 단건 식단 생성 노드 ────────────────────────────────────────────────────────

async def resolve_excluded_names(state: SingleMealState) -> dict:
    """제외 식자재 ID → 이름 변환. ID 없으면 API 호출 생략."""
    excluded_ids = set(state.get("excluded_ingredient_ids", []))
    if not excluded_ids:
        return {"excluded_names": []}
    try:
        async with backend_client(state["auth_token"]) as client:
            resp = await client.get("/ingredients")
            resp.raise_for_status()
            names = [
                item["name"] for item in resp.json()
                if item.get("id") in excluded_ids
            ]
            return {"excluded_names": names}
    except Exception:
        return {"excluded_names": []}


async def retrieve_single_context(state: SingleMealState) -> dict:
    """RAG: 단건 식단용 영양기준·가이드라인 검색."""
    month_num = int(state["meal_date"].split("-")[1])
    meal_type = state["meal_type"]
    nutrition_query = "학교급식 영양기준 에너지 단백질 지방 나트륨 칼슘"
    planning_query = f"{month_num}월 {meal_type} 학교급식 식단 메뉴 구성 계절"
    policy, guidelines = await asyncio.gather(
        asyncio.to_thread(search_joined, "policy", nutrition_query, 5),
        asyncio.to_thread(search_joined, "guidelines", planning_query, 5),
    )
    context = (
        f"[급식 정책 — 영양기준]\n{policy[:_MAX_RAG_CHARS]}\n\n"
        f"[식단 작성 가이드라인]\n{guidelines[:_MAX_RAG_CHARS]}"
    )
    return {"guidelines_context": context}


async def generate_single_meal(state: SingleMealState) -> dict:
    """LLM으로 단건 끼니 식단 생성 — 밥·국·반찬 구조."""
    meal_type = state["meal_type"]
    meal_date = state["meal_date"]
    serving = state["serving_count"]
    target_cal = state.get("target_calories")
    budget = state.get("budget_limit")
    excluded = state.get("excluded_names", [])
    month_num = int(meal_date.split("-")[1])

    if meal_type == "BREAKFAST":
        structure_rule = (
            "조식은 다음 중 하나로 구성합니다:\n"
            "  - 죽 1가지 + 반찬 1~2가지\n"
            "  - 샌드위치·토스트 + 국물 1가지\n"
            "  - 밥 + 국 + 간단한 반찬 1~2가지"
        )
    else:
        structure_rule = (
            "중식·석식은 다음 구성을 반드시 포함합니다:\n"
            "  1. 밥류 1가지 (쌀밥·잡곡밥·볶음밥 등)\n"
            "  2. 국/탕/찌개 1가지\n"
            "  3. 단백질 반찬 1가지 (육류·생선·두부·계란 중심)\n"
            "  4. 채소 반찬 1~2가지"
        )

    excluded_line = f"\n제외 식자재 (절대 사용 금지): {', '.join(excluded)}" if excluded else ""

    system = SystemMessage(content=(
        "당신은 학교급식 영양사입니다. 아래 규정에 따라 한 끼 식단을 JSON으로 구성하세요.\n\n"
        f"【끼니 구성 규정】\n{structure_rule}\n\n"
        "【출력 규칙】\n"
        "- 각 요리(menu)에 name(요리명), description(간단한 설명 1문장), "
        "ingredients(재료 목록)를 포함하세요.\n"
        "- ingredients의 quantity는 급식 인원 수 기준 총량이며 정수로 작성합니다.\n"
        "- unit은 G·KG·ML·L·EA·BOX·PACK·BUNDLE·BAG·CAN·BOTTLE 중 하나를 사용합니다.\n"
        "- reason은 이 끼니를 추천한 이유를 1~3문장으로 작성합니다 "
        "(영양 균형·계절성·식재료 특성 등).\n"
        "- estimated_kcal: 이 끼니 1인분 기준 총 칼로리(kcal) 추정치\n"
        "- estimated_protein_g / estimated_fat_g / estimated_sodium_mg: 1인분 기준 추정치\n"
        "- 한국 학교급식에 적합한 메뉴를 선택하세요."
        f"{excluded_line}"
    ))
    human = HumanMessage(content=(
        f"날짜: {meal_date} ({month_num}월)\n"
        f"끼니: {meal_type}\n"
        f"급식 인원: {serving}명\n"
        f"목표 칼로리: {target_cal or '제한 없음'}kcal/인\n"
        f"예산 제한: {budget or '제한 없음'}원/인\n\n"
        f"[영양 기준 및 가이드라인]\n{state['guidelines_context']}"
    ))

    structured = _get_llm().with_structured_output(SingleMealPlan)
    result: SingleMealPlan = await structured.ainvoke([system, human])
    return {
        "result": result.model_dump(),
        "retry_count": state.get("retry_count", 0) + (1 if state.get("validation_errors") else 0),
    }


async def validate_single_nutrition(state: SingleMealState) -> dict:
    """단건 끼니 영양 검증 — 코드 검사 선행 후 LLM 배치 1회."""
    result = state.get("result") or {}
    menus = result.get("menus", [])
    if not menus:
        return {"validation_errors": []}

    errors: list[dict] = []
    date = state["meal_date"]
    meal_type = state["meal_type"]

    # 1. 코드 레벨 수치 검증
    sodium = result.get("estimated_sodium_mg")
    kcal = result.get("estimated_kcal")
    protein = result.get("estimated_protein_g") or 0
    fat = result.get("estimated_fat_g") or 0

    issues: list[str] = []
    if sodium is not None and sodium > 1000:
        issues.append(f"나트륨 {sodium:.0f}mg 초과(기준 1000mg)")
    if kcal is not None and kcal < 200:
        issues.append(f"에너지 {kcal:.0f}kcal 부족")
    if kcal:
        if not (0.07 <= protein * 4 / kcal <= 0.20):
            issues.append(f"단백질 비율 {protein * 4 / kcal:.0%}(기준 7~20%)")
        if not (0.15 <= fat * 9 / kcal <= 0.30):
            issues.append(f"지방 비율 {fat * 9 / kcal:.0%}(기준 15~30%)")

    if issues:
        errors.append({"date": date, "meal_type": meal_type,
                       "menu": ", ".join(m["name"] for m in menus),
                       "issue": " / ".join(issues)})
        return {"validation_errors": errors}

    # 2. 코드 통과 시 LLM 검증
    docs_list = await asyncio.gather(*[
        asyncio.to_thread(search_food, m["name"], 1) for m in menus
    ])
    lines = [
        f"{i + 1}. {date} [{meal_type}] {m['name']}\n   영양DB: {(docs or '정보없음')[:300]}"
        for i, (m, docs) in enumerate(zip(menus, docs_list))
    ]
    prompt = (
        "각 메뉴가 학교급식 영양 기준(에너지 1/3, 단백질 7~20%, 지방 15~30%, 나트륨 1000mg 이하)을 "
        "충족하는지 판단하고 date·meal_type·menu_name·passed·issue를 반환하세요.\n\n"
        + "\n\n".join(lines)
    )
    structured = _get_llm().with_structured_output(BatchNutritionVerdict)
    verdict: BatchNutritionVerdict = await structured.ainvoke([HumanMessage(content=prompt)])
    errors += [
        {"date": v.date, "meal_type": v.meal_type, "menu": v.menu_name, "issue": v.issue}
        for v in verdict.verdicts if not v.passed
    ]
    return {"validation_errors": errors}


async def check_single_budget(state: SingleMealState) -> dict:
    """단건용 예산 확인 — meal_date의 월 기준으로 조회."""
    month = state["meal_date"][:7]
    try:
        async with backend_client(state["auth_token"]) as client:
            resp = await client.get(f"/budgets?month={month}")
            resp.raise_for_status()
            return {"budget_info": resp.json()}
    except Exception as e:
        return {"budget_info": {"warning": f"예산 조회 실패: {e}"}}


async def save_single_plan(state: SingleMealState) -> dict:
    """단건 식단 저장 — /diets 1회 + menus[] 각 요리마다 /meals POST."""
    result = state.get("result") or {}
    menus = result.get("menus", [])
    if not menus:
        return {"error": "저장할 메뉴가 없습니다"}

    n = len(menus)
    kcal_each = (result.get("estimated_kcal") or 0) / n
    protein_each = (result.get("estimated_protein_g") or 0) / n
    fat_each = (result.get("estimated_fat_g") or 0) / n
    sodium_each = (result.get("estimated_sodium_mg") or 0) / n

    try:
        async with backend_client(state["auth_token"]) as client:
            diet_resp = await client.post("/diets", json={
                "date": state["meal_date"],
                "meal_type": state["meal_type"],
                "school_id": state["school_id"],
            })
            diet_resp.raise_for_status()
            diet_id = diet_resp.json().get("id")
            if diet_id is None:
                raise ValueError("backend /diets response missing 'id' field")

            async def _post_meal(menu):
                resp = await client.post("/meals", json={
                    "diet_id": diet_id,
                    "menu_name": menu["name"],
                    "kcal": kcal_each,
                    "protein": protein_each,
                    "fat": fat_each,
                    "sodium": sodium_each,
                })
                resp.raise_for_status()

            meal_resps = await asyncio.gather(
                *[_post_meal(menu) for menu in menus],
                return_exceptions=True,
            )
            if any(isinstance(r, Exception) for r in meal_resps):
                errs = [r for r in meal_resps if isinstance(r, Exception)]
                try:
                    await client.delete(f"/diets/{diet_id}")
                except Exception:
                    pass
                return {"error": f"메뉴 저장 실패 ({errs[0]}), 롤백 완료"}
    except Exception as e:
        return {"error": f"식단 저장 실패: {e}"}

    return {"error": None}
