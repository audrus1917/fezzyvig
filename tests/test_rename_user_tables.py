"""Проверка переименования таблиц пользователей и сессий."""

from importlib import import_module

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_rename_user_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = import_module("fezzyvig.db.migrations.versions.0007_rename_user_tables")
    metadata = sa.MetaData()
    users = sa.Table(
        "app_user",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
    )
    sa.Index("ix_app_user_email", users.c.email, unique=True)
    sessions = sa.Table(
        "user_session",
        metadata,
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.ForeignKey("app_user.id", ondelete="CASCADE")),
    )
    sa.Index("ix_user_session_user_id", sessions.c.user_id)
    for name in ("employer_oauth_token", "employer_vacancy"):
        sa.Table(
            name,
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.ForeignKey("app_user.id", ondelete="CASCADE")),
        )

    with sa.create_engine("sqlite://").begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        metadata.create_all(connection)
        connection.execute(users.insert().values(id=1, email="user@example.com"))
        connection.execute(sessions.insert().values(token_hash="token", user_id=1))
        for name in ("employer_oauth_token", "employer_vacancy"):
            connection.exec_driver_sql(f"INSERT INTO {name} (id, user_id) VALUES (1, 1)")

        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        inspector = sa.inspect(connection)
        assert {"users", "user_sessions"} <= set(inspector.get_table_names())
        assert {"app_user", "user_session"}.isdisjoint(inspector.get_table_names())
        assert connection.exec_driver_sql("SELECT id, email FROM users").one() == (
            1,
            "user@example.com",
        )
        session_row = connection.exec_driver_sql(
            "SELECT token_hash, user_id FROM user_sessions"
        ).one()
        assert session_row == (
            "token",
            1,
        )
        assert {index["name"] for index in inspector.get_indexes("users")} == {"ix_users_email"}
        assert {index["name"] for index in inspector.get_indexes("user_sessions")} == {
            "ix_user_sessions_user_id"
        }
        for name in ("user_sessions", "employer_oauth_token", "employer_vacancy"):
            assert inspector.get_foreign_keys(name)[0]["referred_table"] == "users"

        migration.downgrade()
        inspector = sa.inspect(connection)
        assert {"app_user", "user_session"} <= set(inspector.get_table_names())
        assert connection.exec_driver_sql("SELECT id FROM app_user").scalar_one() == 1
        assert connection.exec_driver_sql("SELECT user_id FROM user_session").scalar_one() == 1
        assert {index["name"] for index in inspector.get_indexes("app_user")} == {
            "ix_app_user_email"
        }
        assert {index["name"] for index in inspector.get_indexes("user_session")} == {
            "ix_user_session_user_id"
        }
        for name in ("user_session", "employer_oauth_token", "employer_vacancy"):
            assert inspector.get_foreign_keys(name)[0]["referred_table"] == "app_user"
