"""add persisted decision audit records"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d9a8f4e3b2"
down_revision: Union[str, Sequence[str], None] = "a6b5d27525c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_audits",
        sa.Column("decision_id", sa.String(length=64), primary_key=True),
        sa.Column("customer_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("candidate_products", sa.Text(), nullable=False),
        sa.Column("feasible_products", sa.Text(), nullable=False),
        sa.Column("excluded_products", sa.Text(), nullable=False),
        sa.Column("selected_product_id", sa.String(length=50), nullable=True),
        sa.Column("ranking_method", sa.String(length=100), nullable=False),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("approval_status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_decision_audits_customer_id", "decision_audits", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_decision_audits_customer_id", table_name="decision_audits")
    op.drop_table("decision_audits")
