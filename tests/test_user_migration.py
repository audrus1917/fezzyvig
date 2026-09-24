"""Проверка миграции новых полей пользователя."""

from datetime import UTC, datetime
from importlib import import_module

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_user_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    timestamp_migration = import_module("fezzyvig.db.migrations.versions.0004_user_timestamps")
    flags_migration = import_module("fezzyvig.db.migrations.versions.0005_user_flags")
    names_migration = import_module("fezzyvig.db.migrations.versions.0006_user_names")
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    tables = [
        sa.Table(
            name,
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        for name in ("app_user", "user_session")
    ]
    metadata.create_all(engine)

    with engine.begin() as connection:
        created_at = datetime(2020, 1, 1, tzinfo=UTC)
        for table in tables:
            connection.execute(table.insert().values(id=1, created_at=created_at))
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(timestamp_migration, "op", operations)
        monkeypatch.setattr(flags_migration, "op", operations)
        monkeypatch.setattr(names_migration, "op", operations)

        timestamp_migration.upgrade()
        for table in tables:
            columns = {
                column["name"]: column for column in sa.inspect(connection).get_columns(table.name)
            }
            migrated_table = sa.table(table.name, sa.column("created_at"), sa.column("updated_at"))
            row = connection.execute(sa.select(migrated_table)).one()
            assert columns["updated_at"]["nullable"] is False
            assert row._mapping["updated_at"] == row._mapping["created_at"]

        flags_migration.upgrade()
        user_columns = {
            column["name"]: column for column in sa.inspect(connection).get_columns("app_user")
        }
        user_row = connection.execute(sa.text("SELECT is_active, is_superuser FROM app_user")).one()
        assert user_columns["is_active"]["nullable"] is False
        assert user_columns["is_superuser"]["nullable"] is False
        assert user_row._mapping["is_active"] == 1
        assert user_row._mapping["is_superuser"] == 0

        names_migration.upgrade()
        user_columns = {
            column["name"] for column in sa.inspect(connection).get_columns("app_user")
        }
        assert {"first_name", "last_name"} <= user_columns
        assert connection.execute(sa.text("SELECT first_name, last_name FROM app_user")).one() == (
            None,
            None,
        )

        names_migration.downgrade()
        flags_migration.downgrade()
        timestamp_migration.downgrade()
        for table in tables:
            column_names = {
                column["name"] for column in sa.inspect(connection).get_columns(table.name)
            }
            assert "updated_at" not in column_names
            if table.name == "app_user":
                assert "is_active" not in column_names
                assert "is_superuser" not in column_names
                assert "first_name" not in column_names
                assert "last_name" not in column_names
