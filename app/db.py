from __future__ import annotations

import os
from contextlib import contextmanager

_APP_DIR = os.path.dirname(os.path.abspath(__file__))

from sqlalchemy import (
    Boolean,
    String,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    create_engine,
    func,
)
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://hydra:hydra@localhost:5432/hydra",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class OpportunityCandidate(Base):
    __tablename__ = "opportunity_candidates"

    id = Column(Integer, primary_key=True)
    source = Column(Text, nullable=False)
    topic = Column(Text, nullable=False)
    vertical = Column(Text, nullable=False)
    production_format = Column(Text, nullable=False)
    demand_velocity = Column(Numeric, default=0)
    monetization_fit = Column(Numeric, default=0)
    ai_exploitability = Column(Numeric, default=0)
    cross_source_confirmation = Column(Numeric, default=0)
    time_to_revenue = Column(Numeric, default=0)
    saturation_penalty = Column(Numeric, default=0)
    platform_risk_penalty = Column(Numeric, default=0)
    score = Column(Numeric, default=0)
    status = Column(Text, default="new")
    evidence = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, ForeignKey("opportunity_candidates.id"))
    title = Column(Text, nullable=False)
    production_format = Column(Text)
    price = Column(Numeric, default=19)
    status = Column(Text, default="draft")
    gumroad_url = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class ProductArtifact(Base):
    __tablename__ = "product_artifacts"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    artifact_type = Column(Text, nullable=False)
    title = Column(Text)
    content = Column(Text, nullable=False)
    source = Column(Text, default="ruflo")
    # Sprint 1.3 — distribution publish tracking
    published_url = Column(Text)
    published_at = Column(DateTime)
    channel_tag = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class ProductFile(Base):
    __tablename__ = "product_files"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    file_label = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(Text, default="manual")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class RevenueEvent(Base):
    __tablename__ = "revenue_events"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    marketplace = Column(Text, default="gumroad")
    amount = Column(Numeric, nullable=False)
    currency = Column(Text, default="USD")
    event_type = Column(Text, default="sale")
    notes = Column(Text)
    # Sprint 1.3 — attribution
    source_attribution = Column(Text)
    channel_tag = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True)
    entity_type = Column(Text, nullable=False)
    entity_id = Column(Integer, nullable=False)
    decision = Column(Text, nullable=False)
    decided_by = Column(Text, default="operator")
    created_at = Column(DateTime, server_default=func.now())


class SystemFlag(Base):
    __tablename__ = "system_flags"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id = Column(Integer, primary_key=True)
    provider = Column(Text)
    model = Column(Text)
    purpose = Column(Text)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cost_usd = Column(Numeric, default=0)
    duration_ms = Column(Integer)
    status = Column(Text)
    error = Column(Text)
    # Sprint 1.5.1 — structured error classification for operator visibility
    error_type = Column(Text)
    # Raw malformed output is kept for debugging structured-output failures.
    raw_response = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Listing(Base):
    """Multi-platform listing tracker. Sprint 4.0 will add API publish automation."""

    __tablename__ = "listings"

    id = Column(Integer, primary_key=True)
    product_id = Column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    # gumroad | etsy | sellfy | payhip | creative_market
    platform = Column(Text, nullable=False)
    # draft | live | paused | archived
    status = Column(Text, default="draft")
    external_id = Column(Text)     # marketplace-assigned ID once published
    draft_url = Column(Text)
    live_url = Column(Text)
    price_cents = Column(Integer)
    currency = Column(Text, default="USD")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MarketResearchRun(Base):
    __tablename__ = "market_research_runs"

    id = Column(Integer, primary_key=True)
    label = Column(Text, nullable=False)
    source = Column(Text, nullable=False, default="manual")
    category = Column(Text)
    query = Column(Text)
    item_count = Column(Integer, default=0)
    status = Column(Text, nullable=False, default="raw")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MarketResearchItem(Base):
    __tablename__ = "market_research_items"

    id = Column(Integer, primary_key=True)
    run_id = Column(
        Integer,
        ForeignKey("market_research_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(Text, nullable=False)
    shop_name = Column(Text)
    price_cents = Column(Integer)
    currency = Column(Text, default="USD")
    rating = Column(Numeric(3, 2))
    review_count = Column(Integer)
    tags = Column(Text)
    listing_url = Column(Text)
    product_type = Column(Text)
    aesthetic = Column(Text)
    bundle_type = Column(Text)
    pain_point = Column(Text)
    pattern_notes = Column(Text)
    risk_flags = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class MarketPattern(Base):
    __tablename__ = "market_patterns"

    id = Column(Integer, primary_key=True)
    run_id = Column(
        Integer,
        ForeignKey("market_research_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    pattern_type = Column(Text, nullable=False)
    pattern_summary = Column(Text, nullable=False)
    example_titles = Column(Text)
    price_range_low = Column(Integer)
    price_range_high = Column(Integer)
    recommended_modality = Column(Text)
    recommended_marketplace = Column(Text)
    confidence = Column(Text, default="medium")
    used_for_opportunity_id = Column(
        Integer,
        ForeignKey("opportunity_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, server_default=func.now())



# ---------------------------------------------------------------------------
# Sprint 2.7 — ATLAS v0.1: product lifecycle + revenue tracking
# ---------------------------------------------------------------------------

class ProductLifecycle(Base):
    """Tracks each product through the pipeline.

    States: draft → ready → approved → listed → live → paused → archived
    ATLAS v0.1: this table IS Hermes v0.1 state machine.
    """
    __tablename__ = "product_lifecycle"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False, unique=True, index=True)
    product_name = Column(String(255), nullable=True)
    state = Column(
        sa.Enum('draft','ready','approved','listed','live','paused','archived',
                name='lifecycle_state', create_type=False),
        nullable=False, default='draft', index=True)
    gumroad_url = Column(String(500), nullable=True)
    fiverr_url = Column(String(500), nullable=True)
    gumroad_plr_url = Column(String(500), nullable=True)
    first_sale_at = Column(DateTime(timezone=True), nullable=True)
    total_revenue_usd = Column(Numeric(10, 2), nullable=False, default=0)
    sale_count = Column(Integer, nullable=False, default=0)
    refund_count = Column(Integer, nullable=False, default=0)
    operator_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Sale(Base):
    """One row per revenue event — Gumroad webhook or manual entry.

    Minimum viable telemetry: know what sold, when, for how much, from where.
    buyer_email_hash is sha256(lower(email)) — never store raw buyer email.
    """
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False, index=True)
    platform = Column(
        sa.Enum('gumroad','fiverr','payhip','plr_marketplace','other',
                name='sale_platform', create_type=False),
        nullable=False, index=True)
    amount_usd = Column(Numeric(10, 2), nullable=False)
    buyer_email_hash = Column(String(64), nullable=True)
    is_refund = Column(Boolean, nullable=False, default=False)
    refund_reason = Column(Text, nullable=True)
    sale_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    raw_payload = Column(Text, nullable=True)


def init_db() -> None:
    """Initialize the database via Alembic migrations.

    Three cases handled safely:
      1. Fresh DB (no tables)          → run all migrations from scratch
      2. Pre-Alembic DB (has tables,   → stamp head so Alembic won't re-create
         no alembic_version)
      3. Already-managed DB            → upgrade to latest head
    """
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import inspect, text

    alembic_cfg = Config(os.path.join(_APP_DIR, "alembic.ini"))

    with engine.connect() as conn:
        insp = inspect(conn)
        existing_tables = set(insp.get_table_names())
        has_alembic = "alembic_version" in existing_tables
        has_our_tables = "opportunity_candidates" in existing_tables

    if has_our_tables and not has_alembic:
        # Pre-Alembic database: tables exist but Alembic hasn't touched them.
        # Stamp at 0001 (baseline) so Alembic knows the original schema already
        # exists, then upgrade to head so NEW migrations (0002+) actually run.
        # Stamping at "head" would skip all migrations including new ones — wrong.
        command.stamp(alembic_cfg, "0001")
        command.upgrade(alembic_cfg, "head")
    else:
        # Fresh DB (runs all migrations) or already-managed (upgrades to head).
        command.upgrade(alembic_cfg, "head")

    _apply_one_shot_migrations()
    seed_system_flags()


def _apply_one_shot_migrations() -> None:
    """Idempotent ADD COLUMN statements until Alembic lands in Sprint 2.0.

    Postgres' `IF NOT EXISTS` makes each statement safe to re-run on every
    startup. Keep this list short and append-only.
    """
    # Adding a UNIQUE index on product_files (product_id, file_path) was attempted
    # but trips on legacy duplicates from Sprint 1.2 verification runs. Defer to
    # Alembic in Sprint 2.0 with a paired dedupe migration. The export auto-register
    # path already does an explicit existence check before insert.
    statements = [
        "ALTER TABLE revenue_events ADD COLUMN IF NOT EXISTS source_attribution TEXT",
        "ALTER TABLE revenue_events ADD COLUMN IF NOT EXISTS channel_tag TEXT",
        "ALTER TABLE product_artifacts ADD COLUMN IF NOT EXISTS published_url TEXT",
        "ALTER TABLE product_artifacts ADD COLUMN IF NOT EXISTS published_at TIMESTAMP",
        "ALTER TABLE product_artifacts ADD COLUMN IF NOT EXISTS channel_tag TEXT",
        # Sprint 1.5.1 — structured error type for LLM call visibility
        "ALTER TABLE llm_calls ADD COLUMN IF NOT EXISTS error_type TEXT",
        "ALTER TABLE llm_calls ADD COLUMN IF NOT EXISTS raw_response TEXT",
        # Sprint 1.6 — listings table safety net (catches DBs stamped at 0002
        # before migration 0002 actually ran, e.g. pre-Alembic stamp-to-head path)
        """CREATE TABLE IF NOT EXISTS listings (
            id          SERIAL PRIMARY KEY,
            product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            platform    TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'draft',
            external_id TEXT,
            draft_url   TEXT,
            live_url    TEXT,
            price_cents INTEGER,
            currency    TEXT DEFAULT 'USD',
            notes       TEXT,
            created_at  TIMESTAMP DEFAULT now(),
            updated_at  TIMESTAMP DEFAULT now()
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_listings_product_platform ON listings (product_id, platform)",
        # Sprint 1.7 — Marketplace Intelligence safety nets.
        """CREATE TABLE IF NOT EXISTS market_research_runs (
            id SERIAL PRIMARY KEY,
            label TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            category TEXT,
            query TEXT,
            item_count INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'raw',
            notes TEXT,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS market_research_items (
            id SERIAL PRIMARY KEY,
            run_id INTEGER NOT NULL REFERENCES market_research_runs(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            shop_name TEXT,
            price_cents INTEGER,
            currency TEXT DEFAULT 'USD',
            rating NUMERIC(3,2),
            review_count INTEGER,
            tags TEXT,
            listing_url TEXT,
            product_type TEXT,
            aesthetic TEXT,
            bundle_type TEXT,
            pain_point TEXT,
            pattern_notes TEXT,
            risk_flags TEXT,
            created_at TIMESTAMP DEFAULT now()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_market_research_items_run_id ON market_research_items (run_id)",
        """CREATE TABLE IF NOT EXISTS market_patterns (
            id SERIAL PRIMARY KEY,
            run_id INTEGER NOT NULL REFERENCES market_research_runs(id) ON DELETE CASCADE,
            pattern_type TEXT NOT NULL,
            pattern_summary TEXT NOT NULL,
            example_titles TEXT,
            price_range_low INTEGER,
            price_range_high INTEGER,
            recommended_modality TEXT,
            recommended_marketplace TEXT,
            confidence TEXT DEFAULT 'medium',
            used_for_opportunity_id INTEGER REFERENCES opportunity_candidates(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT now()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_market_patterns_run_id ON market_patterns (run_id)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.exec_driver_sql(stmt)


def seed_system_flags() -> None:
    with session_scope() as session:
        defaults = {
            "hydra:kill": "false",
            "daily_budget_usd": "3",
        }
        for key, value in defaults.items():
            if not session.get(SystemFlag, key):
                session.add(SystemFlag(key=key, value=value))


def get_flag_value(key: str, default: str = "") -> str:
    with session_scope() as session:
        flag = session.get(SystemFlag, key)
        return flag.value if flag else default


def set_flag_value(key: str, value: str) -> None:
    with session_scope() as session:
        flag = session.get(SystemFlag, key)
        if flag:
            flag.value = value
        else:
            session.add(SystemFlag(key=key, value=value))


def is_kill_switch_active() -> bool:
    return get_flag_value("hydra:kill", "false").lower() == "true"


def get_daily_budget() -> float:
    try:
        return float(get_flag_value("daily_budget_usd", "3"))
    except ValueError:
        return 3.0


class SystemActionBlocked(RuntimeError):
    """Raised when an action is blocked by the kill switch or another safety gate."""


def assert_system_can_act(action_name: str) -> None:
    """Refuse to act when the kill switch is on. Budget is informational for now."""
    if is_kill_switch_active():
        raise SystemActionBlocked(
            f"Kill switch is active. Refusing action '{action_name}'. "
            f"Disable in Settings before retrying."
        )


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
