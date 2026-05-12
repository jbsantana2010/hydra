"""webhooks.py — Inbound webhook receivers for marketplace platforms.

Sprint 2.7: Gumroad sale webhook only.
Purpose: log every revenue event to the sales table. No automation beyond logging.

Gumroad webhook reference:
  https://help.gumroad.com/article/180-api-webhooks
  POST fields: seller_id, product_id, product_name, price, email, timestamp, ...
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request, Response
from sqlalchemy.orm import Session

from db import ProductLifecycle, Sale, SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_email(email: str | None) -> str | None:
    """One-way hash buyer email — never store raw emails."""
    if not email:
        return None
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def _cents_to_decimal(price_str: str | None) -> Decimal:
    """Gumroad sends price in cents as a string (e.g. '9700' = $97.00)."""
    try:
        return Decimal(str(int(price_str or "0"))) / 100
    except (ValueError, TypeError):
        return Decimal("0")


@router.post("/gumroad")
async def gumroad_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive Gumroad sale/refund webhook and log to sales table.

    Gumroad sends form-encoded POST data. We log it and update product_lifecycle.
    Returns 200 immediately — Gumroad retries on non-2xx.
    """
    # Parse form body (Gumroad sends application/x-www-form-urlencoded)
    try:
        body = await request.form()
        payload = dict(body)
    except Exception as exc:
        logger.error("[webhook/gumroad] Failed to parse body: %s", exc)
        return Response(status_code=200)  # Always 200 to prevent retries

    sale_type = payload.get("sale_id") or payload.get("refund_id")
    is_refund = bool(payload.get("refund_id"))
    email = payload.get("email") or payload.get("buyer_email")
    price_str = payload.get("price")  # cents
    gumroad_product_id = payload.get("product_id", "")
    product_name = payload.get("product_name", "")

    # Map Gumroad product ID to HYDRA product ID
    # Sprint 2.7: manually maintained until ATLAS auto-fills it
    # Update this dict after you create the Gumroad listing and get its product_id
    GUMROAD_PRODUCT_MAP: dict[str, int] = {
        # "gumroad_product_id": hydra_product_id
        # e.g. "abc123": 43
        # Fill in after listing Product 43 on Gumroad
    }
    hydra_product_id = GUMROAD_PRODUCT_MAP.get(gumroad_product_id, 0)
    if not hydra_product_id:
        # Default to 43 if unknown — fine while we have only one product
        logger.warning(
            "[webhook/gumroad] Unknown Gumroad product_id=%s, defaulting to 43. "
            "Update GUMROAD_PRODUCT_MAP in webhooks.py after listing.",
            gumroad_product_id,
        )
        hydra_product_id = 43

    amount = _cents_to_decimal(price_str)
    email_hash = _hash_email(email)

    sale = Sale(
        product_id=hydra_product_id,
        platform="gumroad",
        amount_usd=amount,
        buyer_email_hash=email_hash,
        is_refund=is_refund,
        refund_reason=payload.get("dispute_reason") if is_refund else None,
        sale_at=datetime.now(timezone.utc),
        raw_payload=json.dumps(payload)[:4000],  # truncate for safety
    )
    db.add(sale)

    # Update product_lifecycle
    lc = db.query(ProductLifecycle).filter_by(product_id=hydra_product_id).first()
    if lc:
        if not is_refund:
            if lc.first_sale_at is None:
                lc.first_sale_at = datetime.now(timezone.utc)
                logger.info(
                    "[webhook/gumroad] FIRST SALE — product_id=%d amount=$%s",
                    hydra_product_id, amount,
                )
            lc.sale_count = (lc.sale_count or 0) + 1
            lc.total_revenue_usd = (lc.total_revenue_usd or Decimal("0")) + amount
            if lc.state in ("listed", "approved", "ready"):
                lc.state = "live"
        else:
            lc.refund_count = (lc.refund_count or 0) + 1
            logger.warning(
                "[webhook/gumroad] REFUND — product_id=%d amount=$%s",
                hydra_product_id, amount,
            )

    db.commit()

    logger.info(
        "[webhook/gumroad] %s logged — product=%d amount=$%s email_hash=%s",
        "REFUND" if is_refund else "SALE",
        hydra_product_id, amount, email_hash,
    )

    return Response(status_code=200, content="OK")


@router.post("/fiverr")
async def fiverr_webhook(request: Request, db: Session = Depends(get_db)):
    """Placeholder for Fiverr order notifications.

    Fiverr does not have a native webhook system. This endpoint is for
    manual order logging via internal tooling or a future Fiverr integration.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    product_id = body.get("product_id", 43)
    amount = Decimal(str(body.get("amount_usd", "0")))
    email_hash = _hash_email(body.get("buyer_email"))
    is_refund = body.get("is_refund", False)

    sale = Sale(
        product_id=product_id,
        platform="fiverr",
        amount_usd=amount,
        buyer_email_hash=email_hash,
        is_refund=is_refund,
        sale_at=datetime.now(timezone.utc),
        raw_payload=json.dumps(body)[:4000],
    )
    db.add(sale)

    lc = db.query(ProductLifecycle).filter_by(product_id=product_id).first()
    if lc and not is_refund:
        if lc.first_sale_at is None:
            lc.first_sale_at = datetime.now(timezone.utc)
            logger.info("[webhook/fiverr] FIRST SALE product_id=%d amount=$%s", product_id, amount)
        lc.sale_count = (lc.sale_count or 0) + 1
        lc.total_revenue_usd = (lc.total_revenue_usd or Decimal("0")) + amount
        if lc.state in ("listed", "approved", "ready"):
            lc.state = "live"

    db.commit()
    logger.info("[webhook/fiverr] %s logged product=%d amount=$%s",
                "REFUND" if is_refund else "SALE", product_id, amount)

    return {"status": "ok"}
