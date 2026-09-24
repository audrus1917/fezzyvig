"""Добавить имя и фамилию к существующим пользователям.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Добавить поля имени и фамилии."""
    op.add_column("app_user", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("app_user", sa.Column("last_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Удалить поля имени и фамилии."""
    with op.batch_alter_table("app_user") as batch_op:
        batch_op.drop_column("last_name")
        batch_op.drop_column("first_name")
