"""Общие поля времени моделей базы данных."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from fezzyvig.config.settings import get_settings


def _current_time() -> datetime:
    return datetime.now(get_settings().TZ)


class ChangedAtMixin:
    """Общие поля времени создания и изменения записи."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_current_time, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_current_time, onupdate=_current_time, nullable=False
    )
