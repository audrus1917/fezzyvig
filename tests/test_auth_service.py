"""Тесты аутентификации пользователей и серверных сессий."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fezzyvig.models.base import Base
from fezzyvig.models.user import UserSession
from fezzyvig.services.auth import AuthError, AuthService


@pytest.fixture
def auth_service() -> Iterator[AuthService]:
    """Создать сервис аутентификации при базе данных в памяти."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield AuthService(session, timedelta(days=30))


def test_register_and_session(auth_service: AuthService) -> None:
    """Регистрация хеширует пароль и создаёт доступную для проверки сессию."""
    user = auth_service.register(" User@Example.com ", "secret-pass", " Anna ", " Ivanova ")
    token = auth_service.create_session(user)

    assert user.email == "user@example.com"
    assert user.first_name == "Anna"
    assert user.last_name == "Ivanova"
    assert user.password_hash != "secret-pass"
    assert auth_service.get_user(token) == user


def test_invalid_credentials(auth_service: AuthService) -> None:
    """Аутентификация отклоняет неверный пароль."""
    auth_service.register("user@example.com", "secret-pass")

    with pytest.raises(AuthError, match="Invalid email or password"):
        auth_service.authenticate("user@example.com", "wrong-pass")


def test_duplicate_email(auth_service: AuthService) -> None:
    """Нормализованные адреса электронной почты остаются уникальными."""
    auth_service.register("user@example.com", "secret-pass")

    with pytest.raises(AuthError, match="already exists"):
        auth_service.register("USER@example.com", "another-pass")


def test_inactive_user(auth_service: AuthService) -> None:
    user = auth_service.register("user@example.com", "secret-pass")
    token = auth_service.create_session(user)
    user.is_active = False
    auth_service._session.commit()

    with pytest.raises(AuthError, match="Invalid email or password"):
        auth_service.authenticate("user@example.com", "secret-pass")
    assert auth_service.get_user(token) is None

    user.is_active = True
    auth_service._session.commit()
    assert auth_service.get_user(token) is None


def test_invalid_name(auth_service: AuthService) -> None:
    """Отклонить имя из одних пробелов."""
    with pytest.raises(AuthError, match="Enter a name"):
        auth_service.register("user@example.com", "secret-pass", "   ", "Ivanova")


@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        ("invalid", "secret-pass", "valid email"),
        ("user@example.com", "short", "at least 8"),
        ("user@example.com", "x" * 257, "too long"),
    ],
)
def test_registration_rejects_invalid_input(
    auth_service: AuthService, email: str, password: str, message: str
) -> None:
    with pytest.raises(AuthError, match=message):
        auth_service.register(email, password)


def test_expired_session_is_removed(auth_service: AuthService) -> None:
    user = auth_service.register("user@example.com", "secret-pass")
    token = auth_service.create_session(user)
    token_hash = sha256(token.encode()).hexdigest()
    stored = auth_service._session.get(UserSession, token_hash)
    assert stored is not None
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    auth_service._session.commit()

    assert auth_service.get_user(token) is None
    assert auth_service._session.get(UserSession, token_hash) is None


def test_logout_revokes_session(auth_service: AuthService) -> None:
    user = auth_service.register("user@example.com", "secret-pass")
    token = auth_service.create_session(user)

    auth_service.delete_session(token)

    assert auth_service.get_user(token) is None
    auth_service.delete_session(token)
