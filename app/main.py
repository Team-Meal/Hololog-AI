from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router

app = FastAPI(
    title="Hololog-AI",
    description="학교 급식 AI 월간 식단 추천 서비스",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
