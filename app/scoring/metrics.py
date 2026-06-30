"""
4.2 산식 — 5개 지표 순수 함수.
모든 함수는 외부 호출·LLM 없이 계산 가능.
"""
from __future__ import annotations

from app.scoring.seasonal import is_seasonal


def local_produce_rate(used: list[str], local_set: set[str]) -> float:
    """지역농산물 활용률 (%) = 지역농산물 수 / 전체 식자재 수 × 100"""
    if not used:
        return 0.0
    count = sum(1 for name in used if name in local_set)
    return count / len(used) * 100


def seasonal_rate(used: list[str], month: int) -> float:
    """제철반영률 (%) = 제철 식자재 수 / 전체 식자재 수 × 100"""
    if not used:
        return 0.0
    count = sum(1 for name in used if is_seasonal(name, month))
    return count / len(used) * 100


def cost_per_person(total_cost_krw: float, serving_count: int) -> float:
    """1인단가 (원) = 총 비용 / 급식 인원"""
    if serving_count <= 0:
        return 0.0
    return total_cost_krw / serving_count


def waste_reduction_rate(
    inventory_items: list[str],
    used_items: list[str],
    baseline: float = 0.15,
) -> float:
    """폐기감소율 (%).
    재고 식자재를 많이 활용할수록 예상 폐기 감소율이 높아진다.
    = 재고 활용율 × 기준폐기율(15%) × 100
    """
    if not inventory_items:
        return 0.0
    inventory_set = set(inventory_items)
    used_from_inventory = sum(1 for name in used_items if name in inventory_set)
    utilization = used_from_inventory / len(inventory_items)
    return utilization * baseline * 100


def budget_savings_rate(budget: float, actual_cost: float) -> float:
    """예산절감율 (%) = (예산 - 실제비용) / 예산 × 100"""
    if budget <= 0:
        return 0.0
    return (budget - actual_cost) / budget * 100
