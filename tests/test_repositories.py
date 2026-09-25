"""Проверки хранения пользователей, токенов и вакансий."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from fezzyvig.models.base import Base
from fezzyvig.models.oauth_token import EmployerOAuthToken
from fezzyvig.models.user import User, UserSession
from fezzyvig.models.vacancy import EmployerVacancy
from fezzyvig.repositories.auth import AuthRepository
from fezzyvig.repositories.employer import EmployerRepository


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_auth_repository_session_lifecycle(session: Session) -> None:
    repository = AuthRepository(session)
    user = User(email="user@example.com", password_hash="hash")
    repository.add_user(user)
    session.flush()
    user_id = user.id
    browser_session = UserSession(
        token_hash="token-hash",
        user_id=user_id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    repository.add_session(browser_session)
    session.commit()
    session.expunge_all()

    assert repository.get_user_by_email("user@example.com") is not None
    assert repository.get_user(user_id) is not None
    assert repository.get_user_by_email("missing@example.com") is None
    assert repository.get_session("missing-token") is None
    stored = repository.get_session("token-hash")
    assert stored is not None and stored.user_id == user_id

    repository.delete_session(stored)
    session.commit()
    assert repository.get_session("token-hash") is None
    assert repository.get_user(user_id) is not None


def test_token_repository_isolates_users(session: Session) -> None:
    first = EmployerRepository(session, user_id=1)
    second = EmployerRepository(session, user_id=2)
    for user_id, provider in ((1, "hh"), (1, "other"), (2, "hh")):
        repository = first if user_id == 1 else second
        repository.save_token(
            EmployerOAuthToken(
                user_id=user_id,
                provider=provider,
                access_token=f"access-{user_id}-{provider}",
                refresh_token="refresh",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
    session.commit()
    session.expunge_all()

    first_token = first.get_token()
    second_token = second.get_token(for_update=True)
    assert first_token is not None and first_token.access_token == "access-1-hh"
    assert second_token is not None and second_token.access_token == "access-2-hh"
    assert EmployerRepository(session, user_id=3).get_token() is None


def test_vacancy_repository_filters_and_orders(session: Session) -> None:
    first = EmployerRepository(session, user_id=1)
    second = EmployerRepository(session, user_id=2)
    now = datetime.now(UTC)
    for user_id, source, external_id, synced_at in (
        (1, "hh", "older", now - timedelta(days=1)),
        (1, "hh", "newer", now),
        (1, "other", "shared", now + timedelta(days=1)),
        (2, "hh", "shared", now + timedelta(days=2)),
    ):
        repository = first if user_id == 1 else second
        repository.save_vacancy(
            EmployerVacancy(
                user_id=user_id,
                source=source,
                external_id=external_id,
                title=external_id,
                url="https://example.test/vacancy",
                description="Description",
                synced_at=synced_at,
            )
        )
    session.commit()
    session.expunge_all()

    assert [item.external_id for item in first.list_vacancies()] == [
        "shared", "newer", "older"
    ]
    assert [item.external_id for item in second.list_vacancies()] == ["shared"]
    assert first.get_vacancy("shared") is None
    assert second.get_vacancy("shared") is not None
    assert first.get_vacancy("missing") is None
