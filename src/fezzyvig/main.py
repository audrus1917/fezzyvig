"""Создание и настройка FastAPI-приложения Fezzyvig."""

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response

from fezzyvig.api.auth import router as auth_router
from fezzyvig.api.employer import callback_router
from fezzyvig.api.employer import router as employer_router
from fezzyvig.config.settings import get_settings
from fezzyvig.i18n import translate


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


@app.exception_handler(HTTPException)
async def localized_http_exception(request: Request, exc: HTTPException) -> Response:
    """Перевести текст ошибки API, сохранив её статус и заголовки."""
    if isinstance(exc.detail, str):
        exc = HTTPException(
            status_code=exc.status_code,
            detail=translate(request, exc.detail),
            headers=exc.headers,
        )
    return await http_exception_handler(request, exc)


app.include_router(auth_router)
app.include_router(employer_router)
app.include_router(callback_router)

static_directory = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_directory), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Вернуть главную страницу панели управления."""
    return FileResponse(static_directory / "index.html")


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    """Вернуть отдельную страницу входа."""
    return FileResponse(static_directory / "index.html")


@app.get("/vacancies/{vacancy_id}", include_in_schema=False)
def vacancy_page(vacancy_id: int) -> FileResponse:
    """Вернуть страницу карточки вакансии для клиентского интерфейса."""
    return FileResponse(static_directory / "index.html")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Вернуть базовый индикатор работоспособности приложения."""
    return {"status": "ok"}
