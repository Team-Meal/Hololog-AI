"""
3.2 룰 기반 식자재 스코어링 — LLM 불사용.
제철·가격·재고·선호·예산 5신호를 가중 합산.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.scoring.kamis import get_price_score
from app.scoring.seasonal import is_seasonal

_WEIGHTS = {
    "seasonal":   0.30,
    "price":      0.25,
    "inventory":  0.30,
    "preference": 0.10,
    "budget":     0.05,
}


@dataclass
class ScoredIngredient:
    name: str
    total_score: float
    source_tags: list[str] = field(default_factory=list)


async def score_ingredients(
    ingredients: list[dict],
    excluded_names: list[str],
    month: int,
    budget_limit: int | None,
) -> list[ScoredIngredient]:
    """
    ingredients: GET /ingredients 결과 (각 항목에 'name', 'quantity' 포함)
    반환값: total_score 내림차순 정렬된 ScoredIngredient 목록
    """
    if not ingredients:
        return []

    excluded_set = set(excluded_names)
    from app.core.config import settings
    kamis_available = bool(settings.kamis_api_key)

    # KAMIS 가격 스코어 병렬 조회
    names = [item.get("name", "") for item in ingredients]
    price_scores: list[float] = await asyncio.gather(
        *[get_price_score(name, month) for name in names]
    )

    result: list[ScoredIngredient] = []
    for item, price_score in zip(ingredients, price_scores):
        name = item.get("name", "")
        quantity = item.get("quantity", 0) or 0

        # 각 신호 점수
        s_seasonal = 1.0 if is_seasonal(name, month) else 0.0
        s_price = price_score
        s_inventory = 1.0 if quantity > 0 else 0.0
        s_preference = 0.0 if name in excluded_set else 1.0
        s_budget = 1.0 if budget_limit is not None else 0.5

        total = (
            _WEIGHTS["seasonal"]   * s_seasonal
            + _WEIGHTS["price"]    * s_price
            + _WEIGHTS["inventory"] * s_inventory
            + _WEIGHTS["preference"] * s_preference
            + _WEIGHTS["budget"]   * s_budget
        )

        tags: list[str] = []
        if s_inventory > 0:
            tags.append("[학교재고]")
        if s_seasonal > 0:
            tags.append("[농사로]")
        if kamis_available and price_score != 0.5:
            tags.append("[KAMIS]")

        result.append(ScoredIngredient(name=name, total_score=round(total, 4), source_tags=tags))

    result.sort(key=lambda x: x.total_score, reverse=True)
    return result
