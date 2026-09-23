"""Тесты аутентификации пользователей и серверных сессий."""

from datetime import timedelta

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from fezzyvig.services.auth import AuthError, AuthService


@pytest.fixture
def auth_service() -> AuthService:
    """Создать сервис аутентификации при базе данных в памяти."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield AuthService(session, timedelta(days=30))


def test_register_and_session(auth_service: AuthService) -> None:
    """Регистрация хеширует пароль и создаёт доступную для проверки сессию."""
    user = auth_service.register(" User@Example.com ", "secret-pass")
    token = auth_service.create_session(user)

    assert user.email == "user@example.com"
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
