"""Модели хранения вакансий работодателя."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fezzyvig.models.base import Base


class EmployerVacancy(Base):
    """Вакансия, импортированная из аккаунта работодателя на HeadHunter."""

    __tablename__ = "vacancies"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "source", "external_id", name="uq_vacancies_user_source_id"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(50), default="hh", index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), default="")
    area_name: Mapped[str | None] = mapped_column(String(255))
    employment_form_name: Mapped[str | None] = mapped_column(String(100))
    vacancy_type_name: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2048))
    description: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, object]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
