"""Тесты API аутентификации и защищённых маршрутов работодателя."""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fezzyvig.db.database import get_session
from fezzyvig.main import app
from fezzyvig.models.base import Base


def test_authentication_flow() -> None:
    """Браузерная сессия открывает и прекращает доступ к данным работодателя."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    try:
        with TestClient(app, base_url="https://testserver") as client:
            english_error = client.get("/employer/vacancies")
            assert english_error.status_code == 401
            assert english_error.json()["detail"] == "Authentication required"
            russian_error = client.get("/auth/me", headers={"Accept-Language": "ru-RU, en;q=0.8"})
            assert russian_error.status_code == 401
            assert russian_error.json()["detail"] == "Требуется авторизация"
            assert client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "secret-pass"},
            ).status_code == 422

            registered = client.post(
                "/auth/register",
                json={
                    "email": "user@example.com",
                    "password": "secret-pass",
                    "first_name": "Anna",
                    "last_name": "Ivanova",
                },
            )
            assert registered.status_code == 201
            assert registered.json()["email"] == "user@example.com"
            assert registered.json()["first_name"] == "Anna"
            assert registered.json()["last_name"] == "Ivanova"
            invalid_login = client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "wrong-password"},
                headers={"Accept-Language": "ru"},
            )
            assert invalid_login.status_code == 401
            assert invalid_login.json()["detail"] == "Неверный адрес электронной почты или пароль"
            assert client.get("/auth/me").json()["first_name"] == "Anna"
            assert client.get("/employer/vacancies").json() == []

            assert client.post("/auth/logout").status_code == 204
            assert client.get("/auth/me").status_code == 401
            logged_in = client.post(
                "/auth/login", json={"email": "user@example.com", "password": "secret-pass"}
            )
            assert logged_in.status_code == 200
            assert logged_in.json()["last_name"] == "Ivanova"
    finally:
        app.dependency_overrides.clear()
