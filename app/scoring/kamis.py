"""
KAMIS(농산물유통정보) 가격 스코어 조회 — 선택적 통합.
KAMIS_API_KEY 환경변수가 없으면 0.5(중립)를 반환하고 네트워크 호출을 하지 않는다.
"""
from __future__ import annotations

import httpx

_KAMIS_URL = "https://www.kamis.or.kr/service/price/xml.do"


async def get_price_score(ingredient_name: str, month: int) -> float:
    """0.0(비쌈) ~ 1.0(저렴) 상대 점수. 키 미설정 또는 오류 시 0.5 반환."""
    from app.core.config import settings

    if not settings.kamis_api_key:
        return 0.5

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                _KAMIS_URL,
                params={
                    "action": "dailySalesList",
                    "p_cert_key": settings.kamis_api_key,
                    "p_cert_id": "2024",
                    "p_returntype": "json",
                    "p_itemname": ingredient_name,
                    "p_convert_kg_yn": "Y",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        items = (
            data.get("data", {})
            .get("item", [])
        )
        if not items:
            return 0.5

        # 당일가격과 평년가격 비교 — 저렴할수록 점수 높음
        today_prices = [
            float(item.get("dpr1", "0").replace(",", ""))
            for item in items
            if item.get("dpr1") and item["dpr1"] not in ("-", "")
        ]
        avg_prices = [
            float(item.get("dpr7", "0").replace(",", ""))
            for item in items
            if item.get("dpr7") and item["dpr7"] not in ("-", "")
        ]
        if not today_prices or not avg_prices:
            return 0.5

        today = sum(today_prices) / len(today_prices)
        avg = sum(avg_prices) / len(avg_prices)
        if avg <= 0:
            return 0.5

        # today < avg → 저렴 → 점수 > 0.5
        ratio = today / avg
        score = max(0.0, min(1.0, 1.0 - (ratio - 0.5)))
        return score

    except Exception:
        return 0.5
