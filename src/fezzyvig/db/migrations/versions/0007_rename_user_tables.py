"""Переименовать таблицы пользователей и сессий.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Переименовать таблицы и индексы без потери записей."""
    op.rename_table("app_user", "users")
    op.rename_table("user_session", "user_sessions")
    op.drop_index("ix_app_user_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.drop_index("ix_user_session_user_id", table_name="user_sessions")
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])


def downgrade() -> None:
    """Вернуть прежние имена таблиц и индексов."""
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.create_index("ix_user_session_user_id", "user_sessions", ["user_id"])
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_app_user_email", "users", ["email"], unique=True)
    op.rename_table("user_sessions", "user_session")
    op.rename_table("users", "app_user")
