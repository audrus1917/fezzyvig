"""Добавление хранилища OAuth-токенов работодателя.

Идентификатор ревизии: 0002
Предыдущая ревизия: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Создать таблицу активных OAuth-токенов работодателя."""
    op.create_table(
        "employer_oauth_token",
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider"),
    )


def downgrade() -> None:
    """Удалить хранилище OAuth-токенов работодателя."""
    op.drop_table("employer_oauth_token")
