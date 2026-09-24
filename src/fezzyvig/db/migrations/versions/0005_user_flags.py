"""Добавление признаков активности и суперпользователя.

Идентификатор ревизии: 0005
Предыдущая ревизия: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Сохранить доступ существующих пользователей без выдачи им прав администратора."""
    op.add_column("app_user", sa.Column("is_active", sa.Boolean(), nullable=True))
    op.add_column("app_user", sa.Column("is_superuser", sa.Boolean(), nullable=True))
    users = sa.table("app_user", sa.column("is_active"), sa.column("is_superuser"))
    op.execute(users.update().values(is_active=True, is_superuser=False))
    with op.batch_alter_table("app_user") as batch_op:
        batch_op.alter_column("is_active", nullable=False)
        batch_op.alter_column("is_superuser", nullable=False)


def downgrade() -> None:
    """Удалить признаки активности и суперпользователя."""
    with op.batch_alter_table("app_user") as batch_op:
        batch_op.drop_column("is_superuser")
        batch_op.drop_column("is_active")
