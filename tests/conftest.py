from collections.abc import AsyncIterator, Callable
from pathlib import Path

import httpx
import pytest_asyncio
from fastapi import FastAPI

from app.config import Settings
from app.main import create_app
from app.services.llm import LLMClient

AppFactory = Callable[[LLMClient | None], FastAPI]


@pytest_asyncio.fixture
async def app_factory(tmp_path: Path) -> AsyncIterator[AppFactory]:
    counter = 0

    def factory(llm: LLMClient | None = None) -> FastAPI:
        nonlocal counter
        counter += 1
        settings = Settings(database_url=f"sqlite:///{tmp_path / f'test-{counter}.db'}")
        return create_app(settings=settings, llm_client=llm)

    yield factory


@pytest_asyncio.fixture
async def client(app_factory: AppFactory) -> AsyncIterator[httpx.AsyncClient]:
    app = app_factory(None)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client
