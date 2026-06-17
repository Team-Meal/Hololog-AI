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


def main() -> None:
    print("=== Hololog-AI 식단 생성 CLI ===\n")

    month = ask("대상 월 (YYYY-MM)", "2026-07")
    school_id = ask("학교 ID", "1")
    token = ask("인증 토큰 (없으면 Enter)", "test")

    print(f"\n요청 중... (POST {BASE_URL}/agent/generate-plan)\n")

    try:
        resp = httpx.post(
            f"{BASE_URL}/agent/generate-plan",
            json={"month": month, "school_id": int(school_id)},
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
        print(f"\n오류: {data['error']}")

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


if __name__ == "__main__":
    main()
