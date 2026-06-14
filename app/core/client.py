from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import httpx

from app.core.config import settings


@asynccontextmanager
async def backend_client(auth_token: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(
        base_url=settings.backend_url,
        headers=headers,
        timeout=30.0,
    ) as client:
        yield client
