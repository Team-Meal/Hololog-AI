"""
로컬 테스트용 CLI.
실행: uv run python test/cli.py
"""
import json
import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def run_generate_plan() -> None:
    month = ask("대상 월 (YYYY-MM)", "2026-07")
    school_id = ask("학교 ID", "1")
    token = ask("인증 토큰 (없으면 Enter)", "test")
    holidays_raw = ask("추가 휴무일 (공휴일 자동제외, 학교 재량휴업일만 입력. 쉼표 구분 YYYY-MM-DD)", "")
    holidays = [h.strip() for h in holidays_raw.split(",") if h.strip()]

    print(f"\n요청 중... (POST {BASE_URL}/agent/generate-plan)\n")

    try:
        resp = httpx.post(
            f"{BASE_URL}/agent/generate-plan",
            json={"month": month, "school_id": int(school_id), "holidays": holidays},
            headers={"Authorization": f"Bearer {token}"},
            timeout=300.0,
        )
    except httpx.ConnectError:
        print(f"서버에 연결할 수 없습니다. {BASE_URL} 에서 서버가 실행 중인지 확인하세요.")
        sys.exit(1)

    print(f"HTTP {resp.status_code}\n")

    if resp.status_code != 200:
        print(f"오류: {resp.text}")
        sys.exit(1)

    data = resp.json()

    print(f"월: {data['month']}")
    print(f"총 식단 수: {data['total_meals']}")

    if data.get("error"):
        print(f"\n경고: {data['error']}")

    if data.get("validation_errors"):
        print(f"\n영양 검증 실패 {len(data['validation_errors'])}건:")
        for e in data["validation_errors"]:
            print(f"  - {e.get('date')} {e.get('meal_type')}: {e.get('issue')}")

    if data.get("budget_info"):
        budget = data["budget_info"]
        if "warning" in budget:
            print(f"\n예산 조회 경고: {budget['warning']}")
        else:
            print(f"\n예산 정보: {json.dumps(budget, ensure_ascii=False, indent=2)}")

    print("\n--- 생성된 식단 ---")
    for meal in data.get("meal_plan", []):
        print(
            f"  {meal.get('date')} [{meal.get('meal_type'):8}] "
            f"{meal.get('menu_name')} "
            f"({meal.get('estimated_kcal')}kcal)"
        )

    save = ask("\n전체 결과를 JSON으로 저장할까요? (y/N)", "N")
    if save.lower() == "y":
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        default_path = result_dir / f"meal_plan_{month}.json"
        path = ask("저장 경로", str(default_path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"저장 완료: {path}")


def run_recommend_meal() -> None:
    meal_date = ask("날짜 (YYYY-MM-DD)", "2026-07-01")
    meal_type_raw = ask("끼니 (1=BREAKFAST / 2=LUNCH / 3=DINNER)", "2")
    meal_type_map = {"1": "BREAKFAST", "2": "LUNCH", "3": "DINNER"}
    meal_type = meal_type_map.get(meal_type_raw, meal_type_raw.upper())

    school_id = ask("학교 ID", "1")
    token = ask("인증 토큰 (없으면 Enter)", "test")
    serving_count = ask("급식 인원", "100")

    target_cal_raw = ask("목표 칼로리 kcal/인 (없으면 Enter)", "")
    target_calories = int(target_cal_raw) if target_cal_raw else None

    budget_raw = ask("예산 제한 원/인 (없으면 Enter)", "")
    budget_limit = int(budget_raw) if budget_raw else None

    excluded_raw = ask("제외 식자재 ID (쉼표 구분, 없으면 Enter)", "")
    excluded_ids = [int(x.strip()) for x in excluded_raw.split(",") if x.strip()]

    print(f"\n요청 중... (POST {BASE_URL}/agent/recommend-meal)\n")

    try:
        resp = httpx.post(
            f"{BASE_URL}/agent/recommend-meal",
            json={
                "mealDate": meal_date,
                "mealType": meal_type,
                "schoolId": int(school_id),
                "servingCount": int(serving_count),
                "targetCalories": target_calories,
                "budgetLimit": budget_limit,
                "excludedIngredientIds": excluded_ids,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=300.0,
        )
    except httpx.ConnectError:
        print(f"서버에 연결할 수 없습니다. {BASE_URL} 에서 서버가 실행 중인지 확인하세요.")
        sys.exit(1)

    print(f"HTTP {resp.status_code}\n")

    if resp.status_code != 200:
        print(f"오류: {resp.text}")
        sys.exit(1)

    data = resp.json()

    print(f"끼니: {data['mealType']}  날짜: {data['mealDate']}")

    menus = data.get("menus", [])
    print(f"메뉴 {len(menus)}가지:")
    for i, menu in enumerate(menus, 1):
        ingredients_str = ", ".join(
            f"{ing['name']} {ing['quantity']}{ing['unit']}"
            for ing in menu.get("ingredients", [])
        )
        print(f"  {i}. {menu['name']} — {ingredients_str}")
        if menu.get("description"):
            print(f"     {menu['description']}")

    if data.get("reason"):
        print(f"\n추천 이유: {data['reason']}")

    if data.get("error"):
        print(f"\n경고: {data['error']}")

    save = ask("\n전체 결과를 JSON으로 저장할까요? (y/N)", "N")
    if save.lower() == "y":
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        default_path = result_dir / f"recommend_meal_{meal_date}_{meal_type}.json"
        path = ask("저장 경로", str(default_path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"저장 완료: {path}")


def main() -> None:
    print("=== Hololog-AI 식단 생성 CLI ===\n")
    print("1. 월간 식단 생성")
    print("2. 단건 식단 추천")
    choice = ask("\n선택", "1")

    print()
    if choice == "2":
        run_recommend_meal()
    else:
        run_generate_plan()


if __name__ == "__main__":
    main()
