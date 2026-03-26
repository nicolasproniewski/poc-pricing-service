"""add rate_type to sofr_rates

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rate_type column, defaulting existing rows to 'overnight'
    op.add_column(
        "sofr_rates",
        sa.Column(
            "rate_type",
            sa.String(length=10),
            nullable=False,
            server_default="overnight",
        ),
    )
    # Swap unique constraint: (rate_date) → (rate_date, rate_type)
    op.drop_constraint("uq_sofr_rate_date", "sofr_rates", type_="unique")
    op.create_unique_constraint(
        "uq_sofr_rate_date_type", "sofr_rates", ["rate_date", "rate_type"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_sofr_rate_date_type", "sofr_rates", type_="unique")
    op.create_unique_constraint("uq_sofr_rate_date", "sofr_rates", ["rate_date"])
    op.drop_column("sofr_rates", "rate_type")
