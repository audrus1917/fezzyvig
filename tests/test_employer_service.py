"""Тесты синхронизации данных работодателя HeadHunter."""

import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import httpx
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from fezzyvig.models.oauth_token import EmployerOAuthToken
from fezzyvig.models.vacancy import EmployerVacancy
from fezzyvig.services.employer import EmployerService


def test_sync_vacancies_upserts() -> None:
    """Повторная синхронизация обновляет существующую вакансию."""
    payloads = iter(
        [
            {
                "items": [
                    {
                        "id": "42",
                        "name": "Python Developer",
                        "employer": {"name": "Acme"},
                        "alternate_url": "https://hh.ru/vacancy/42",
                        "snippet": {"requirement": "Python"},
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": "42",
                        "name": "Senior Python Developer",
                        "employer": {"name": "Acme"},
                        "alternate_url": "https://hh.ru/vacancy/42",
                        "snippet": {"requirement": "Python and PostgreSQL"},
                    }
                ]
            },
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/employer/vacancies"
        return httpx.Response(200, json=next(payloads))

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    client = httpx.AsyncClient(
        base_url="https://api.hh.ru",
        transport=httpx.MockTransport(handler),
    )
    try:
        with Session(engine) as session:
            service = EmployerService(session, client, user_id=1)
            assert asyncio.run(service.sync_vacancies()) == 1
            assert asyncio.run(service.sync_vacancies()) == 1

            vacancies = list(session.exec(select(EmployerVacancy)).all())
            assert len(vacancies) == 1
            assert vacancies[0].title == "Senior Python Developer"
    finally:
        asyncio.run(client.aclose())


def test_pkce_values_are_unique() -> None:
    """Каждая попытка OAuth получает уникальные состояние и верификатор."""
    first = EmployerService.create_pkce()
    second = EmployerService.create_pkce()

    assert first[0] != second[0]
    assert first[1] != second[1]
    assert "=" not in first[2]


def test_exchange_persists_tokens() -> None:
    """Обмен кода авторизации сохраняет пару токенов."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/token"
        form = parse_qs(request.content.decode())
        assert form["grant_type"] == ["authorization_code"]
        assert form["code_verifier"] == ["verifier"]
        return httpx.Response(
            200,
            json={
                "access_token": "access-1",
                "refresh_token": "refresh-1",
                "expires_in": 3600,
                "token_type": "bearer",
            },
        )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    client = httpx.AsyncClient(
        base_url="https://api.hh.ru",
        transport=httpx.MockTransport(handler),
    )
    try:
        with Session(engine) as session:
            service = EmployerService(session, client, user_id=1)
            access_token = asyncio.run(
                service.exchange_code(
                    "code",
                    "verifier",
                    "client-id",
                    "client-secret",
                    "https://example.test/callback",
                )
            )

            token = session.exec(
                select(EmployerOAuthToken).where(EmployerOAuthToken.user_id == 1)
            ).one()
            assert access_token == "access-1"
            assert token is not None
            assert token.access_token == "access-1"
            assert token.refresh_token == "refresh-1"
            assert token.expires_at > datetime.now(UTC).replace(tzinfo=None)
    finally:
        asyncio.run(client.aclose())


def test_sync_refreshes_token() -> None:
    """Синхронизация обновляет просроченный токен до запроса к HeadHunter."""
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/token":
            form = parse_qs(request.content.decode())
            assert form == {
                "grant_type": ["refresh_token"],
                "refresh_token": ["refresh-1"],
            }
            return httpx.Response(
                200,
                json={
                    "access_token": "access-2",
                    "refresh_token": "refresh-2",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
            )
        assert request.headers["Authorization"] == "Bearer access-2"
        return httpx.Response(200, json={"items": []})

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    client = httpx.AsyncClient(
        base_url="https://api.hh.ru",
        transport=httpx.MockTransport(handler),
    )
    try:
        with Session(engine) as session:
            session.add(
                EmployerOAuthToken(
                    user_id=1,
                    access_token="access-1",
                    refresh_token="refresh-1",
                    expires_at=datetime.now(UTC) - timedelta(seconds=1),
                )
            )
            session.commit()
            service = EmployerService(session, client, user_id=1)

            assert asyncio.run(service.sync_vacancies()) == 0

            token = session.exec(
                select(EmployerOAuthToken).where(EmployerOAuthToken.user_id == 1)
            ).one()
            assert requests == ["/token", "/employer/vacancies"]
            assert token is not None
            assert token.access_token == "access-2"
            assert token.refresh_token == "refresh-2"
    finally:
        asyncio.run(client.aclose())


def test_sync_retries_expired_token() -> None:
    """Синхронизация обновляет токен, отклонённый HeadHunter как просроченный."""
    vacancy_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal vacancy_requests
        if request.url.path == "/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "access-2",
                    "refresh_token": "refresh-2",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
            )
        vacancy_requests += 1
        if vacancy_requests == 1:
            assert request.headers["Authorization"] == "Bearer access-1"
            return httpx.Response(
                403,
                json={"errors": [{"type": "oauth", "value": "token_expired"}]},
            )
        assert request.headers["Authorization"] == "Bearer access-2"
        return httpx.Response(200, json={"items": []})

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    client = httpx.AsyncClient(
        base_url="https://api.hh.ru",
        transport=httpx.MockTransport(handler),
    )
    try:
        with Session(engine) as session:
            session.add(
                EmployerOAuthToken(
                    user_id=1,
                    access_token="access-1",
                    refresh_token="refresh-1",
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )
            session.commit()
            service = EmployerService(session, client, user_id=1)

            assert asyncio.run(service.sync_vacancies()) == 0
            assert vacancy_requests == 2
    finally:
        asyncio.run(client.aclose())
