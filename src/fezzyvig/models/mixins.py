"""Общие поля моделей SQLModel."""

from datetime import datetime
from typing import cast

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from fezzyvig.config.settings import get_settings


def _current_time() -> datetime:
    return datetime.now(get_settings().TZ)


class ChangedAtMixin(SQLModel):
    """Общие поля времени создания и изменения записи."""

    # SQLModel принимает экземпляр типа SQLAlchemy, но аннотация sa_type требует класс.
    created_at: datetime = Field(
        default_factory=_current_time,
        sa_type=cast(type[DateTime], DateTime(timezone=True)),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=_current_time,
        sa_type=cast(type[DateTime], DateTime(timezone=True)),
        nullable=False,
        sa_column_kwargs={"onupdate": _current_time},
    )
