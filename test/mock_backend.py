"""
Mock 백엔드 서버 (localhost:8080).
실행: uv run python test/mock_backend.py
"""
import itertools

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock Backend")

# ── 더미 식자재 데이터 ──────────────────────────────────────────────────────────

_INGREDIENTS = [
    {"id": 1,  "name": "쌀",      "quantity": 50,  "unit": "kg"},
    {"id": 2,  "name": "김치",     "quantity": 20,  "unit": "kg"},
    {"id": 3,  "name": "돼지고기", "quantity": 15,  "unit": "kg"},
    {"id": 4,  "name": "닭고기",   "quantity": 20,  "unit": "kg"},
    {"id": 5,  "name": "두부",     "quantity": 10,  "unit": "kg"},
    {"id": 6,  "name": "계란",     "quantity": 200, "unit": "개"},
    {"id": 7,  "name": "감자",     "quantity": 15,  "unit": "kg"},
    {"id": 8,  "name": "당근",     "quantity": 8,   "unit": "kg"},
    {"id": 9,  "name": "양파",     "quantity": 10,  "unit": "kg"},
    {"id": 10, "name": "배추",     "quantity": 20,  "unit": "kg"},
    {"id": 11, "name": "고등어",   "quantity": 10,  "unit": "kg"},
    {"id": 12, "name": "멸치",     "quantity": 3,   "unit": "kg"},
    {"id": 13, "name": "된장",     "quantity": 5,   "unit": "kg"},
    {"id": 14, "name": "고추장",   "quantity": 3,   "unit": "kg"},
    {"id": 15, "name": "간장",     "quantity": 3,   "unit": "L"},
    {"id": 16, "name": "참기름",   "quantity": 1,   "unit": "L"},
    {"id": 17, "name": "콩나물",   "quantity": 8,   "unit": "kg"},
    {"id": 18, "name": "시금치",   "quantity": 5,   "unit": "kg"},
    {"id": 19, "name": "무",       "quantity": 10,  "unit": "kg"},
    {"id": 20, "name": "버섯",     "quantity": 5,   "unit": "kg"},
    {"id": 21, "name": "잡곡",     "quantity": 2,   "unit": "kg"},
]

# ── ID 자동 증가 + 인메모리 저장소 ─────────────────────────────────────────────

_id_counter = itertools.count(1)
_diets: dict[int, dict] = {}
_meals: dict[int, dict] = {}


# ── 요청/응답 스키마 ────────────────────────────────────────────────────────────

class DietRequest(BaseModel):
    date: str
    meal_type: str
    school_id: int


class MealRequest(BaseModel):
    diet_id: int
    menu_name: str
    kcal: float
    protein: float
    fat: float
    sodium: float


# ── 엔드포인트 ─────────────────────────────────────────────────────────────────

@app.get("/ingredients")
def get_ingredients():
    return _INGREDIENTS


@app.get("/budgets")
def get_budgets(month: str = ""):
    return {
        "month": month,
        "total": 5_000_000,
        "used": 1_200_000,
        "remaining": 3_800_000,
        "currency": "KRW",
    }


@app.post("/diets", status_code=201)
def create_diet(body: DietRequest):
    id_ = next(_id_counter)
    _diets[id_] = {"id": id_, "date": body.date, "meal_type": body.meal_type}
    return _diets[id_]


@app.post("/meals", status_code=201)
def create_meal(body: MealRequest):
    id_ = next(_id_counter)
    meal = {"id": id_, "diet_id": body.diet_id, "menu_name": body.menu_name}
    _meals[id_] = meal
    return meal


@app.delete("/diets/{diet_id}")
def delete_diet(diet_id: int):
    deleted = _diets.pop(diet_id, None)
    if deleted is None:
        raise HTTPException(status_code=404, detail=f"diet {diet_id} not found")
    to_delete = [mid for mid, m in _meals.items() if m.get("diet_id") == diet_id]
    for mid in to_delete:
        _meals.pop(mid, None)
    return {"deleted": diet_id}


if __name__ == "__main__":
    uvicorn.run("test.mock_backend:app", host="0.0.0.0", port=8080, reload=False)
