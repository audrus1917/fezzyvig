"""Пользователи приложения и аутентифицированные сессии."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlmodel import Field

from fezzyvig.models.mixins import ChangedAtMixin


class User(ChangedAtMixin, table=True):
    """Пользователь, имеющий доступ к кабинету работодателя."""

    __tablename__ = "app_user"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=320, unique=True, index=True)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    password_hash: str = Field(sa_column=Column(Text, nullable=False), repr=False)
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)


class UserSession(ChangedAtMixin, table=True):
    """Браузерная сессия, которую можно завершить на сервере."""

    __tablename__ = "user_session"  # pyright: ignore[reportAssignmentType]

    token_hash: str = Field(max_length=64, primary_key=True, repr=False)
    user_id: int = Field(
        sa_column=Column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
