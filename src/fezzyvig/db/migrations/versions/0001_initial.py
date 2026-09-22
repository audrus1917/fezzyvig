"""Создание хранилища вакансий работодателя.

Идентификатор ревизии: 0001
Предыдущая ревизия:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Создать таблицу вакансий работодателя и поисковые индексы."""
    op.create_table(
        "employer_vacancy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_employer_vacancy_source_id"),
    )
    op.create_index("ix_employer_vacancy_source", "employer_vacancy", ["source"])
    op.create_index("ix_employer_vacancy_external_id", "employer_vacancy", ["external_id"])
    op.create_index("ix_employer_vacancy_title", "employer_vacancy", ["title"])


def downgrade() -> None:
    """Удалить хранилище вакансий работодателя."""
    op.drop_table("employer_vacancy")
