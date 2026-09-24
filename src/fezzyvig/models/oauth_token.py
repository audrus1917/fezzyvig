"""Модель хранения OAuth-токенов HeadHunter."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fezzyvig.models.base import Base


class EmployerOAuthToken(Base):
    """Активная пара OAuth-токенов работодателя."""

    __tablename__ = "employer_oauth_token"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_employer_oauth_token_user_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="hh")
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
