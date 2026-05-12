"""Sprint 2.7 — Launch telemetry: sales + product_lifecycle tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-11

Tables added:
  product_lifecycle  — tracks each product through the pipeline (ATLAS v0.1 state machine)
  sales              — logs every revenue event from Gumroad/Fiverr webhooks
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

# Enum for product lifecycle states
LIFECYCLE_STATES = (
    "draft",       # being generated
    "ready",       # generation complete, awaiting operator review
    "approved",    # operator approved, ready to list
    "listed",      # listing created on platform (not yet confirmed live)
    "live",        # confirmed live on at least one platform
    "paused",      # temporarily pulled from listing
    "archived",    # no longer active
)

PLATFORMS = ("gumroad", "fiverr", "payhip", "plr_marketplace", "other")


def upgrade() -> None:
    # product_lifecycle — one row per product, tracks pipeline state
    op.create_table(
        "product_lifecycle",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column(
            "state",
            sa.Enum(*LIFECYCLE_STATES, name="lifecycle_state"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("gumroad_url", sa.String(500), nullable=True),
        sa.Column("fiverr_url", sa.String(500), nullable=True),
        sa.Column("gumroad_plr_url", sa.String(500), nullable=True),
        sa.Column("first_sale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_revenue_usd", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("sale_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refund_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("operator_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_product_lifecycle_product_id", "product_lifecycle", ["product_id"], unique=True)
    op.create_index("ix_product_lifecycle_state", "product_lifecycle", ["state"])

    # sales — one row per revenue event (webhook hit or manual entry)
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "platform",
            sa.Enum(*PLATFORMS, name="sale_platform"),
            nullable=False,
        ),
        sa.Column("amount_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("buyer_email_hash", sa.String(64), nullable=True),  # sha256, not raw email
        sa.Column("is_refund", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("refund_reason", sa.Text(), nullable=True),
        sa.Column("sale_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("raw_payload", sa.Text(), nullable=True),  # full webhook JSON for debugging
    )
    op.create_index("ix_sales_product_id", "sales", ["product_id"])
    op.create_index("ix_sales_sale_at", "sales", ["sale_at"])
    op.create_index("ix_sales_platform", "sales", ["platform"])

    # Seed Product 43 as 'ready' — generation complete, waiting for operator to list
    op.execute("""
        INSERT INTO product_lifecycle
            (product_id, product_name, state, operator_notes)
        VALUES
            (43, 'Real Estate AI Mastery Kit', 'approved',
             'Sprint 2.7: LLM content generated, ZIP built, launch package ready. List on Gumroad and Fiverr.')
    """)


def downgrade() -> None:
    op.drop_table("sales")
    op.drop_table("product_lifecycle")
    op.execute("DROP TYPE IF EXISTS lifecycle_state")
    op.execute("DROP TYPE IF EXISTS sale_platform")
