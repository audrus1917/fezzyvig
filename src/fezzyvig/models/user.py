"""Пользователи приложения и аутентифицированные сессии."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from fezzyvig.models.base import Base
from fezzyvig.models.mixins import ChangedAtMixin


class User(ChangedAtMixin, Base):
    """Пользователь, имеющий доступ к кабинету работодателя."""

    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UserSession(ChangedAtMixin, Base):
    """Браузерная сессия, которую можно завершить на сервере."""

    __tablename__ = "user_session"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
