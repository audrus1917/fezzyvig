"""Проверки общих полей моделей."""

from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fezzyvig.config.settings import Settings
from fezzyvig.models import mixins
from fezzyvig.models.base import Base
from fezzyvig.models.user import User


def test_changed_at_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mixins, "get_settings", lambda: Settings(tz_name="Asia/Tokyo"))
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        record = User(email="user@example.com", password_hash="hash")
        session.add(record)
        session.flush()

        assert record.created_at.tzinfo == ZoneInfo("Asia/Tokyo")
        assert record.updated_at.tzinfo == ZoneInfo("Asia/Tokyo")


def test_updated_at_on_change() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(email="user@example.com", password_hash="hash")
        session.add(user)
        session.flush()
        assert user.is_active is True
        assert user.is_superuser is False
        user.updated_at = user.updated_at.replace(year=2000)
        session.commit()

        user.email = "new@example.com"
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.updated_at.year > 2000
