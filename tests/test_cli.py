"""Тесты команды создания пользователя."""

import io
import sys
from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fezzyvig import cli
from fezzyvig.db import database
from fezzyvig.models.base import Base
from fezzyvig.services.auth import AuthService


@pytest.fixture
def user_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Подменить базу команды изолированной базой в памяти."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database, "engine", engine)


def test_add_user_with_argument(user_database: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([
        "USER@example.com", "--password", "secret-pass",
        "--first-name", "Anna", "--last-name", "Ivanova",
    ]) == 0

    with Session(database.engine) as session:
        user = AuthService(session, timedelta(days=30)).authenticate(
            "user@example.com", "secret-pass"
        )

    assert user.email == "user@example.com"
    assert user.first_name == "Anna"
    assert user.last_name == "Ivanova"
    assert "secret-pass" not in capsys.readouterr().out


def test_add_user_from_stdin(
    user_database: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("piped-secret\n"))

    assert cli.main(["user@example.com"]) == 0

    with Session(database.engine) as session:
        user = AuthService(session, timedelta(days=30)).authenticate(
            "user@example.com", "piped-secret"
        )

    assert user.email == "user@example.com"
    assert "piped-secret" not in capsys.readouterr().out


def test_add_user_without_password(
    user_database: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))

    assert cli.main(["user@example.com"]) == 1
    assert "Password is required" in capsys.readouterr().err
