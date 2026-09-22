"""Add users, browser sessions, and per-user employer data.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create authentication tables and scope employer records to users."""
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_app_user_email", "app_user", ["email"], unique=True)
    op.create_table(
        "user_session",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"])

    op.add_column("employer_vacancy", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_employer_vacancy_user_id",
        "employer_vacancy",
        "app_user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_employer_vacancy_user_id", "employer_vacancy", ["user_id"])
    op.drop_constraint("uq_employer_vacancy_source_id", "employer_vacancy", type_="unique")
    op.create_unique_constraint(
        "uq_employer_vacancy_user_source_id",
        "employer_vacancy",
        ["user_id", "source", "external_id"],
    )

    op.add_column(
        "employer_oauth_token",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
    )
    op.add_column("employer_oauth_token", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_employer_oauth_token_user_id",
        "employer_oauth_token",
        "app_user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_employer_oauth_token_user_id", "employer_oauth_token", ["user_id"])
    op.drop_constraint("employer_oauth_token_pkey", "employer_oauth_token", type_="primary")
    op.create_primary_key("pk_employer_oauth_token", "employer_oauth_token", ["id"])
    op.create_unique_constraint(
        "uq_employer_oauth_token_user_provider",
        "employer_oauth_token",
        ["user_id", "provider"],
    )


def downgrade() -> None:
    """Remove authentication tables and per-user ownership columns."""
    op.drop_constraint(
        "uq_employer_oauth_token_user_provider", "employer_oauth_token", type_="unique"
    )
    op.drop_constraint("pk_employer_oauth_token", "employer_oauth_token", type_="primary")
    op.create_primary_key("employer_oauth_token_pkey", "employer_oauth_token", ["provider"])
    op.drop_index("ix_employer_oauth_token_user_id", table_name="employer_oauth_token")
    op.drop_constraint(
        "fk_employer_oauth_token_user_id", "employer_oauth_token", type_="foreignkey"
    )
    op.drop_column("employer_oauth_token", "user_id")
    op.drop_column("employer_oauth_token", "id")

    op.drop_constraint("uq_employer_vacancy_user_source_id", "employer_vacancy", type_="unique")
    op.create_unique_constraint(
        "uq_employer_vacancy_source_id", "employer_vacancy", ["source", "external_id"]
    )
    op.drop_index("ix_employer_vacancy_user_id", table_name="employer_vacancy")
    op.drop_constraint("fk_employer_vacancy_user_id", "employer_vacancy", type_="foreignkey")
    op.drop_column("employer_vacancy", "user_id")

    op.drop_table("user_session")
    op.drop_index("ix_app_user_email", table_name="app_user")
    op.drop_table("app_user")
