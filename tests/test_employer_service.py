"""Тесты синхронизации данных работодателя HeadHunter."""

import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fezzyvig.config.settings import Settings
from fezzyvig.models.base import Base
from fezzyvig.models.oauth_token import EmployerOAuthToken
from fezzyvig.models.vacancy import EmployerVacancy
from fezzyvig.repositories.employer import EmployerRepository
from fezzyvig.services.employer import EmployerService, EmployerSyncError, InvalidOAuthStateError


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
    Base.metadata.create_all(engine)
    client = httpx.AsyncClient(
        base_url="https://api.hh.ru",
        transport=httpx.MockTransport(handler),
    )
    try:
        with Session(engine) as session:
            service = EmployerService(session, client, user_id=1)
            assert asyncio.run(service.sync_vacancies("/employer/vacancies")) == 1
            assert asyncio.run(service.sync_vacancies("/employer/vacancies")) == 1

            vacancies = list(session.scalars(select(EmployerVacancy)).all())
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


def test_oauth_state_is_user_bound() -> None:
    settings = Settings(hh_client_id="client", hh_redirect_uri="https://example.test/main")
    states: dict[str, tuple[str, float, int]] = {}
    client = httpx.AsyncClient()
    try:
        with Session() as session:
            service = EmployerService(session, client, user_id=1)
            url = service.authorization_url(settings, states)
            state = parse_qs(urlparse(url).query)["state"][0]

            assert states[state][2] == 1
            with pytest.raises(InvalidOAuthStateError):
                asyncio.run(
                    EmployerService(session, client, user_id=2).complete_authorization(
                        "code", state, settings, states
                    )
                )
            assert state not in states
    finally:
        asyncio.run(client.aclose())


def test_complete_authorization_consumes_state() -> None:
    settings = Settings(
        hh_client_id="client",
        hh_client_secret=SecretStr("secret"),
        hh_redirect_uri="https://example.test/main",
    )
    states: dict[str, tuple[str, float, int]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode())
        assert form["code_verifier"] == [verifier]
        return httpx.Response(
            200,
            json={"access_token": "access", "refresh_token": "refresh", "expires_in": 3600},
        )

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    client = httpx.AsyncClient(base_url="https://api.hh.ru", transport=httpx.MockTransport(handler))
    try:
        with Session(engine) as session:
            service = EmployerService(session, client, user_id=1)
            query = urlparse(service.authorization_url(settings, states)).query
            state = parse_qs(query)["state"][0]
            verifier = states[state][0]

            asyncio.run(service.complete_authorization("code", state, settings, states))

            assert state not in states
            token = EmployerRepository(session, 1).get_token()
            assert token is not None and token.access_token == "access"
            with pytest.raises(InvalidOAuthStateError):
                asyncio.run(service.complete_authorization("code", state, settings, states))
    finally:
        asyncio.run(client.aclose())


def test_sync_rejects_invalid_items() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    client = httpx.AsyncClient(
        base_url="https://api.hh.ru",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"items": {}})),
    )
    try:
        with Session(engine) as session:
            service = EmployerService(session, client, user_id=1)
            with pytest.raises(EmployerSyncError, match="Unable to load employer vacancies"):
                asyncio.run(service.sync_vacancies("/employer/vacancies"))
            assert service.list_vacancies() == []
    finally:
        asyncio.run(client.aclose())


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
    Base.metadata.create_all(engine)
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

            token = session.scalars(
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
    Base.metadata.create_all(engine)
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

            assert asyncio.run(service.sync_vacancies("/employer/vacancies")) == 0

            token = session.scalars(
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
    Base.metadata.create_all(engine)
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
