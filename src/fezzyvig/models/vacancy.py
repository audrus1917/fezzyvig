"""Модели хранения вакансий работодателя."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class EmployerVacancy(SQLModel, table=True):
    """Вакансия, импортированная из аккаунта работодателя на HeadHunter."""

    __tablename__ = "employer_vacancy"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "source", "external_id", name="uq_employer_vacancy_user_source_id"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None,
        sa_column=Column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=True, index=True),
    )
    source: str = Field(default="hh", max_length=50, index=True)
    external_id: str = Field(max_length=255, index=True)
    title: str = Field(max_length=255, index=True)
    company: str = Field(default="", max_length=255)
    url: str = Field(max_length=2048)
    description: str = Field(sa_column=Column(Text, nullable=False))
    raw_payload: dict[str, object] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    published_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    synced_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
