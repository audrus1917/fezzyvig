"""Create and configure the Fezzyvig FastAPI application."""

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fezzyvig.api.auth import router as auth_router
from fezzyvig.api.employer import callback_router
from fezzyvig.api.employer import router as employer_router
from fezzyvig.config.settings import get_settings


def configure_logging(level: str) -> None:
    """Направить журналы приложения в стандартный вывод процесса."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Инициализировать общий клиент HeadHunter."""
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.oauth_states = {}
    async with httpx.AsyncClient(
        base_url="https://api.hh.ru",
        timeout=httpx.Timeout(settings.http_timeout),
        headers={"HH-User-Agent": settings.hh_user_agent},
    ) as hh_client:
        app.state.hh_client = hh_client
        yield


app = FastAPI(title="Fezzyvig", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(employer_router)
app.include_router(callback_router)

static_directory = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_directory), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Вернуть главную страницу панели управления."""
    return FileResponse(static_directory / "index.html")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Вернуть базовый индикатор работоспособности приложения."""
    return {"status": "ok"}
