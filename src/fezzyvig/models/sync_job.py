"""Задачи синхронизации вакансий работодателя."""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from fezzyvig.models.base import Base
from fezzyvig.models.mixins import ChangedAtMixin


class SyncJob(ChangedAtMixin, Base):
    """Состояние фоновой синхронизации отдельного пользователя."""

    __tablename__ = "sync_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    synced: Mapped[int | None] = mapped_column(Integer, nullable=True)
