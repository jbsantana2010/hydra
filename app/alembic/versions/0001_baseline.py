"""Baseline — all 8 tables from Sprint 1.4.

Revision ID: 0001
Revises:
Create Date: 2026-05-09

This migration captures the full schema that was previously managed by
Base.metadata.create_all(). On a pre-Alembic database that already has
these tables, init_db() stamps this revision with `alembic stamp head`
instead of running this upgrade().
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
        "opportunity_candidates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("vertical", sa.Text, nullable=False),
        sa.Column("production_format", sa.Text, nullable=False),
        sa.Column("demand_velocity", sa.Numeric, server_default="0"),
        sa.Column("monetization_fit", sa.Numeric, server_default="0"),
        sa.Column("ai_exploitability", sa.Numeric, server_default="0"),
        sa.Column("cross_source_confirmation", sa.Numeric, server_default="0"),
        sa.Column("time_to_revenue", sa.Numeric, server_default="0"),
        sa.Column("saturation_penalty", sa.Numeric, server_default="0"),
        sa.Column("platform_risk_penalty", sa.Numeric, server_default="0"),
        sa.Column("score", sa.Numeric, server_default="0"),
        sa.Column("status", sa.Text, server_default="new"),
        sa.Column("evidence", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("opportunity_id", sa.Integer,
                  sa.ForeignKey("opportunity_candidates.id")),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("production_format", sa.Text),
        sa.Column("price", sa.Numeric, server_default="19"),
        sa.Column("status", sa.Text, server_default="draft"),
        sa.Column("gumroad_url", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "product_artifacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("artifact_type", sa.Text, nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source", sa.Text, server_default="ruflo"),
        sa.Column("published_url", sa.Text),
        sa.Column("published_at", sa.DateTime),
        sa.Column("channel_tag", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "product_files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("file_label", sa.Text, nullable=False),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("file_type", sa.Text, server_default="manual"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "revenue_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("marketplace", sa.Text, server_default="gumroad"),
        sa.Column("amount", sa.Numeric, nullable=False),
        sa.Column("currency", sa.Text, server_default="USD"),
        sa.Column("event_type", sa.Text, server_default="sale"),
        sa.Column("notes", sa.Text),
        sa.Column("source_attribution", sa.Text),
        sa.Column("channel_tag", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("decided_by", sa.Text, server_default="operator"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "system_flags",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("provider", sa.Text),
        sa.Column("model", sa.Text),
        sa.Column("purpose", sa.Text),
        sa.Column("prompt_tokens", sa.Integer, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, server_default="0"),
        sa.Column("cost_usd", sa.Numeric, server_default="0"),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("status", sa.Text),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("llm_calls")
    op.drop_table("system_flags")
    op.drop_table("approvals")
    op.drop_table("revenue_events")
    op.drop_table("product_files")
    op.drop_table("product_artifacts")
    op.drop_table("products")
    op.drop_table("opportunity_candidates")
