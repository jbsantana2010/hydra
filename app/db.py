from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    create_engine,
    func,
)
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


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    seed_system_flags()


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
