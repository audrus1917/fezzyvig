"""Test authentication API and protected employer routes."""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from fezzyvig.db.database import get_session
from fezzyvig.main import app


def test_authentication_flow() -> None:
    """A browser session grants and revokes access to employer data."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

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

            registered = client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "secret-pass"},
            )
            assert registered.status_code == 201
            assert registered.json()["email"] == "user@example.com"
            invalid_login = client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "wrong-password"},
                headers={"Accept-Language": "ru"},
            )
            assert invalid_login.status_code == 401
            assert invalid_login.json()["detail"] == "Неверный адрес электронной почты или пароль"
            assert client.get("/auth/me").status_code == 200
            assert client.get("/employer/vacancies").json() == []

            assert client.post("/auth/logout").status_code == 204
            assert client.get("/auth/me").status_code == 401
    finally:
        app.dependency_overrides.clear()
