"""Sprint 1.7 — Marketplace Intelligence tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-10

Tables added:
  market_research_runs   — one row per research session
  market_research_items  — one row per listing/product observed
  market_patterns        — extracted winning patterns (LLM output)
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_research_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False, server_default="manual"),
        sa.Column("category", sa.Text),
        sa.Column("query", sa.Text),
        sa.Column("item_count", sa.Integer, server_default="0"),
        sa.Column("status", sa.Text, nullable=False, server_default="raw"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "market_research_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "run_id", sa.Integer,
            sa.ForeignKey("market_research_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("shop_name", sa.Text),
        sa.Column("price_cents", sa.Integer),
        sa.Column("currency", sa.Text, server_default="USD"),
        sa.Column("rating", sa.Numeric(3, 2)),
        sa.Column("review_count", sa.Integer),
        sa.Column("tags", sa.Text),
        sa.Column("listing_url", sa.Text),
        sa.Column("product_type", sa.Text),
        sa.Column("aesthetic", sa.Text),
        sa.Column("bundle_type", sa.Text),
        sa.Column("pain_point", sa.Text),
        sa.Column("pattern_notes", sa.Text),
        sa.Column("risk_flags", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_market_research_items_run_id",
        "market_research_items", ["run_id"],
    )

    op.create_table(
        "market_patterns",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "run_id", sa.Integer,
            sa.ForeignKey("market_research_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pattern_type", sa.Text, nullable=False),
        sa.Column("pattern_summary", sa.Text, nullable=False),
        sa.Column("example_titles", sa.Text),
        sa.Column("price_range_low", sa.Integer),
        sa.Column("price_range_high", sa.Integer),
        sa.Column("recommended_modality", sa.Text),
        sa.Column("recommended_marketplace", sa.Text),
        sa.Column("confidence", sa.Text, server_default="medium"),
        sa.Column(
            "used_for_opportunity_id", sa.Integer,
            sa.ForeignKey("opportunity_candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_market_patterns_run_id",
        "market_patterns", ["run_id"],
    )


def downgrade() -> None:
    op.drop_table("market_patterns")
    op.drop_table("market_research_items")
    op.drop_table("market_research_runs")
