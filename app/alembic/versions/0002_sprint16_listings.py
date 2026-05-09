"""Sprint 1.6 — add listings table for multi-platform tracking.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-09

Adds the `listings` table that tracks draft/live state per product per
marketplace. Supports: gumroad, etsy, sellfy, payhip, creative_market.
Sprint 4.0 will add API publish automation on top of this table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer,
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # gumroad | etsy | sellfy | payhip | creative_market
        sa.Column("platform", sa.Text, nullable=False),
        # draft | live | paused | archived
        sa.Column("status", sa.Text, server_default="draft", nullable=False),
        sa.Column("external_id", sa.Text),     # marketplace-assigned ID once published
        sa.Column("draft_url", sa.Text),
        sa.Column("live_url", sa.Text),
        sa.Column("price_cents", sa.Integer),
        sa.Column("currency", sa.Text, server_default="USD"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime,
                  server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    # One listing per (product, platform) to avoid accidental duplicates
    op.create_index(
        "ix_listings_product_platform",
        "listings",
        ["product_id", "platform"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_listings_product_platform", table_name="listings")
    op.drop_table("listings")
