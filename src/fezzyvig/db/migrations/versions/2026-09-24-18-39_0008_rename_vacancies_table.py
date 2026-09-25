"""Переименовать таблицу вакансий и связанные объекты.

Идентификатор ревизии: 0008
Предыдущая ревизия: 0007
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Переименовать таблицу, ограничение и индексы вакансий."""
    op.rename_table("employer_vacancy", "vacancies")
    with op.batch_alter_table("vacancies") as batch_op:
        batch_op.drop_constraint("uq_employer_vacancy_user_source_id", type_="unique")
        batch_op.create_unique_constraint(
            "uq_vacancies_user_source_id", ["user_id", "source", "external_id"]
        )
    for column in ("source", "external_id", "title", "user_id"):
        op.drop_index(f"ix_employer_vacancy_{column}", table_name="vacancies")
        op.create_index(f"ix_vacancies_{column}", "vacancies", [column])


def downgrade() -> None:
    """Вернуть прежние имена таблицы, ограничения и индексов."""
    for column in ("source", "external_id", "title", "user_id"):
        op.drop_index(f"ix_vacancies_{column}", table_name="vacancies")
        op.create_index(f"ix_employer_vacancy_{column}", "vacancies", [column])
    with op.batch_alter_table("vacancies") as batch_op:
        batch_op.drop_constraint("uq_vacancies_user_source_id", type_="unique")
        batch_op.create_unique_constraint(
            "uq_employer_vacancy_user_source_id", ["user_id", "source", "external_id"]
        )
    op.rename_table("vacancies", "employer_vacancy")
