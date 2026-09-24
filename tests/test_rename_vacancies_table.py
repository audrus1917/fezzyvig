"""Проверка переименования таблицы вакансий."""

from importlib import import_module

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_rename_vacancies_table(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = import_module(
        "fezzyvig.db.migrations.versions.2026-09-24-18-39_0008_rename_vacancies_table"
    )
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    vacancies = sa.Table(
        "employer_vacancy",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.UniqueConstraint(
            "user_id", "source", "external_id", name="uq_employer_vacancy_user_source_id"
        ),
    )
    for column in ("source", "external_id", "title", "user_id"):
        sa.Index(f"ix_employer_vacancy_{column}", vacancies.c[column])

    with sa.create_engine("sqlite://").begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        metadata.create_all(connection)
        connection.execute(users.insert().values(id=1))
        connection.execute(
            vacancies.insert().values(
                id=1, user_id=1, source="hh", external_id="123", title="Developer"
            )
        )
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))

        migration.upgrade()
        inspector = sa.inspect(connection)
        assert "vacancies" in inspector.get_table_names()
        assert "employer_vacancy" not in inspector.get_table_names()
        assert connection.exec_driver_sql("SELECT user_id, external_id FROM vacancies").one() == (
            1,
            "123",
        )
        assert inspector.get_foreign_keys("vacancies")[0]["referred_table"] == "users"
        assert {item["name"] for item in inspector.get_unique_constraints("vacancies")} == {
            "uq_vacancies_user_source_id"
        }
        assert {item["name"] for item in inspector.get_indexes("vacancies")} == {
            f"ix_vacancies_{column}"
            for column in ("source", "external_id", "title", "user_id")
        }

        migration.downgrade()
        inspector = sa.inspect(connection)
        assert "employer_vacancy" in inspector.get_table_names()
        assert "vacancies" not in inspector.get_table_names()
        restored_row = connection.exec_driver_sql(
            "SELECT user_id, external_id FROM employer_vacancy"
        ).one()
        assert restored_row == (
            1,
            "123",
        )
        assert inspector.get_foreign_keys("employer_vacancy")[0]["referred_table"] == "users"
        assert {item["name"] for item in inspector.get_unique_constraints("employer_vacancy")} == {
            "uq_employer_vacancy_user_source_id"
        }
        assert {item["name"] for item in inspector.get_indexes("employer_vacancy")} == {
            f"ix_employer_vacancy_{column}"
            for column in ("source", "external_id", "title", "user_id")
        }
