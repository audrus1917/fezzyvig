"""Application users and authenticated sessions."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """A user allowed to access the employer workspace."""

    __tablename__ = "app_user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=320, unique=True, index=True)
    password_hash: str = Field(sa_column=Column(Text, nullable=False), repr=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class UserSession(SQLModel, table=True):
    """A revocable server-side browser session."""

    __tablename__ = "user_session"

    token_hash: str = Field(max_length=64, primary_key=True, repr=False)
    user_id: int = Field(
        sa_column=Column(ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
