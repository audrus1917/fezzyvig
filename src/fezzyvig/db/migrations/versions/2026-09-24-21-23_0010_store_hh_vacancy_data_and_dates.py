"""Сохранить полный ответ HH и даты вакансий.

Идентификатор ревизии: 0010
Предыдущая ревизия: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Переименовать JSON в data и добавить поля для карточки вакансии."""
    op.alter_column(
        "vacancies",
        "raw_payload",
        new_column_name="data",
        existing_type=sa.JSON(),
        existing_nullable=False,
    )
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column(
            "vacancies",
            "data",
            type_=postgresql.JSONB(),
            existing_type=sa.JSON(),
            existing_nullable=False,
            postgresql_using="data::jsonb",
        )
    op.add_column("vacancies", sa.Column("area_name", sa.String(length=255), nullable=True))
    op.add_column(
        "vacancies", sa.Column("employment_form_name", sa.String(length=100), nullable=True)
    )
    op.add_column("vacancies", sa.Column("vacancy_type_name", sa.String(length=100), nullable=True))
    op.add_column("vacancies", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("vacancies", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            UPDATE vacancies SET
                area_name = data->'area'->>'name',
                employment_form_name = data->'employment_form'->>'name',
                vacancy_type_name = data->'type'->>'name',
                created_at = NULLIF(data->>'created_at', '')::timestamptz,
                published_at = COALESCE(
                    published_at, NULLIF(data->>'published_at', '')::timestamptz
                ),
                expires_at = NULLIF(data->>'expires_at', '')::timestamptz
            """
        )


def downgrade() -> None:
    """Вернуть прежнюю колонку JSON и удалить извлечённые поля."""
    with op.batch_alter_table("vacancies") as batch_op:
        batch_op.drop_column("expires_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("vacancy_type_name")
        batch_op.drop_column("employment_form_name")
        batch_op.drop_column("area_name")
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column(
            "vacancies",
            "data",
            type_=sa.JSON(),
            existing_type=postgresql.JSONB(),
            existing_nullable=False,
            postgresql_using="data::json",
        )
    op.alter_column(
        "vacancies",
        "data",
        new_column_name="raw_payload",
        existing_type=sa.JSON(),
        existing_nullable=False,
    )
