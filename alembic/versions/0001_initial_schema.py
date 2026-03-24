"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "btc_prices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("price_usd", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_btc_prices_fetched_at", "btc_prices", ["fetched_at"])

    op.create_table(
        "sofr_rates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("rate_pct", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rate_date", name="uq_sofr_rate_date"),
    )


def downgrade() -> None:
    op.drop_table("sofr_rates")
    op.drop_index("ix_btc_prices_fetched_at", table_name="btc_prices")
    op.drop_table("btc_prices")
