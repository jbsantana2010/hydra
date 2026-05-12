"""atlas.py — ATLAS v0.1: Product distribution assistant.

Sprint 2.7: Minimal viable implementation.
- get_product_state(): read lifecycle state for a product
- set_product_state(): update lifecycle state
- get_launch_summary(): return a dict suitable for operator review
- record_listing_url(): write Gumroad/Fiverr URLs to product_lifecycle

ATLAS grows into a full distribution agent in later sprints.
Right now it is a thin DB wrapper + launch package helper.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from db import ProductLifecycle, Sale

logger = logging.getLogger(__name__)

VALID_STATES = ("draft", "ready", "approved", "listed", "live", "paused", "archived")


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def get_product_lifecycle(db: Session, product_id: int) -> ProductLifecycle | None:
    return db.query(ProductLifecycle).filter_by(product_id=product_id).first()


def set_product_state(db: Session, product_id: int, state: str, notes: str | None = None) -> ProductLifecycle:
    """Transition a product to a new lifecycle state."""
    if state not in VALID_STATES:
        raise ValueError(f"Invalid state '{state}'. Valid: {VALID_STATES}")

    lc = db.query(ProductLifecycle).filter_by(product_id=product_id).first()
    if not lc:
        lc = ProductLifecycle(product_id=product_id, state=state)
        db.add(lc)
    else:
        old_state = lc.state
        lc.state = state
        logger.info("[atlas] Product %d: %s → %s", product_id, old_state, state)

    if notes:
        lc.operator_notes = notes
    lc.updated_at = datetime.now(timezone.utc)
    db.commit()
    return lc


def record_listing_url(db: Session, product_id: int, platform: str, url: str) -> None:
    """Record where a product was listed. Updates state to 'listed' if not already live."""
    lc = db.query(ProductLifecycle).filter_by(product_id=product_id).first()
    if not lc:
        lc = ProductLifecycle(product_id=product_id, state="listed")
        db.add(lc)

    if platform == "gumroad":
        lc.gumroad_url = url
    elif platform == "fiverr":
        lc.fiverr_url = url
    elif platform == "gumroad_plr":
        lc.gumroad_plr_url = url

    if lc.state in ("draft", "ready", "approved"):
        lc.state = "listed"

    lc.updated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("[atlas] Product %d listed on %s: %s", product_id, platform, url)


# ---------------------------------------------------------------------------
# Revenue queries
# ---------------------------------------------------------------------------

def get_revenue_summary(db: Session, product_id: int) -> dict:
    """Return a revenue snapshot for a product."""
    lc = db.query(ProductLifecycle).filter_by(product_id=product_id).first()
    sales = db.query(Sale).filter_by(product_id=product_id, is_refund=False).all()
    refunds = db.query(Sale).filter_by(product_id=product_id, is_refund=True).all()

    total_gross = sum(s.amount_usd for s in sales)
    total_refunded = sum(r.amount_usd for r in refunds)

    return {
        "product_id": product_id,
        "product_name": lc.product_name if lc else "Unknown",
        "state": lc.state if lc else "unknown",
        "sale_count": len(sales),
        "refund_count": len(refunds),
        "gross_revenue_usd": float(total_gross),
        "net_revenue_usd": float(total_gross - total_refunded),
        "first_sale_at": lc.first_sale_at.isoformat() if (lc and lc.first_sale_at) else None,
        "gumroad_url": lc.gumroad_url if lc else None,
        "fiverr_url": lc.fiverr_url if lc else None,
    }


def get_launch_summary(db: Session, product_id: int) -> dict:
    """Return a complete launch status summary for operator review."""
    product_dir = Path(f"/app/products/product_{product_id}")
    if not product_dir.exists():
        product_dir = Path(f"products/product_{product_id}")

    launch_dir = product_dir / "launch"
    covers_dir = product_dir / "covers"

    png_files = list(covers_dir.glob("*.png")) if covers_dir.exists() else []
    zip_files = [f for f in product_dir.glob("*.zip") if "Kit_Kit" not in f.name] if product_dir.exists() else []
    launch_ready = launch_dir.exists() and (launch_dir / "LAUNCH_CHECKLIST.md").exists()

    revenue = get_revenue_summary(db, product_id)

    return {
        **revenue,
        "launch_package_ready": launch_ready,
        "png_count": len(png_files),
        "delivery_zip": zip_files[0].name if zip_files else None,
        "delivery_zip_size_kb": (zip_files[0].stat().st_size // 1024) if zip_files else None,
    }
