"""Проверка сохранности данных при изменении колонок вакансий."""

import json
from importlib import import_module

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from fezzyvig.models.vacancy import EmployerVacancy


def test_vacancy_data_migration(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = import_module(
        "fezzyvig.db.migrations.versions.2026-09-24-21-23_0010_store_hh_vacancy_data_and_dates"
    )
    metadata = sa.MetaData()
    vacancies = sa.Table(
        "vacancies",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("raw_payload", sa.JSON, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    payload = {"id": "123", "created_at": "2026-08-28T09:05:47+0300"}

    with sa.create_engine("sqlite://").begin() as connection:
        metadata.create_all(connection)
        connection.execute(vacancies.insert().values(id=1, raw_payload=payload))
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))

        migration.upgrade()
        columns = {column["name"] for column in sa.inspect(connection).get_columns("vacancies")}
        assert {
            "data",
            "area_name",
            "employment_form_name",
            "vacancy_type_name",
            "created_at",
            "expires_at",
        } <= columns
        assert (
            json.loads(connection.exec_driver_sql("SELECT data FROM vacancies").scalar_one())
            == payload
        )

        migration.downgrade()
        columns = {column["name"] for column in sa.inspect(connection).get_columns("vacancies")}
        assert "raw_payload" in columns
        assert "data" not in columns
        assert (
            json.loads(connection.exec_driver_sql("SELECT raw_payload FROM vacancies").scalar_one())
            == payload
        )


def test_vacancy_data_is_jsonb() -> None:
    sql = str(CreateTable(EmployerVacancy.__table__).compile(dialect=postgresql.dialect()))
    assert "data JSONB" in sql
