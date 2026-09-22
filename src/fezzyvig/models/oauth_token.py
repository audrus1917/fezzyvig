"""Модель хранения OAuth-токенов HeadHunter."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class EmployerOAuthToken(SQLModel, table=True):
    """Активная пара OAuth-токенов работодателя."""

    __tablename__ = "employer_oauth_token"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_employer_oauth_token_user_provider"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None,
        sa_column=Column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=True, index=True),
    )
    provider: str = Field(default="hh", max_length=50)
    access_token: str = Field(sa_column=Column(Text, nullable=False), repr=False)
    refresh_token: str = Field(sa_column=Column(Text, nullable=False), repr=False)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
