"""Добавление времени изменения пользователей и браузерных сессий.

Идентификатор ревизии: 0004
Предыдущая ревизия: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Добавить время изменения, сохранив существующие записи."""
    for table_name in ("app_user", "user_session"):
        op.add_column(
            table_name,
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        table = sa.table(table_name, sa.column("created_at"), sa.column("updated_at"))
        op.execute(table.update().values(updated_at=table.c.created_at))
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("updated_at", nullable=False)


def downgrade() -> None:
    """Удалить время изменения пользователей и браузерных сессий."""
    for table_name in ("user_session", "app_user"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("updated_at")
