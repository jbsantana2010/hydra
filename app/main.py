from __future__ import annotations

import base64
import os
import re
import secrets
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select

from db import (
    Approval,
    OpportunityCandidate,
    Product,
    ProductArtifact,
    ProductFile,
    RevenueEvent,
    SystemActionBlocked,
    assert_system_can_act,
    get_daily_budget,
    init_db,
    is_kill_switch_active,
    session_scope,
    set_flag_value,
)
from ruflo_bridge import build_ruflo_listing_prompt, build_ruflo_product_prompt
from signal_engine import calculate_score, mock_candidates

EXPORT_ROOT = Path(os.getenv("HYDRA_EXPORT_ROOT", "exports"))

app = FastAPI(title="HYDRA Console", version="0.1.0")
templates = Jinja2Templates(directory="templates")

PRODUCT_STATUSES = ["draft", "generated", "listed", "live", "paused", "archived"]
ARTIFACT_TYPES = ["outline", "product_content", "listing_copy", "qa_review", "distribution_post"]


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    expected_user = os.getenv("HYDRA_BASIC_USER", "admin")
    expected_pass = os.getenv("HYDRA_BASIC_PASS", "change-me")
    auth_header = request.headers.get("authorization", "")

    if _valid_basic_auth(auth_header, expected_user, expected_pass):
        return await call_next(request)

    return Response(
        "Authentication required",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="HYDRA"'},
    )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "hydra-console"}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/opportunities", status_code=303)


@app.get("/opportunities")
def opportunities(request: Request):
    with session_scope() as session:
        candidates = session.scalars(
            select(OpportunityCandidate).order_by(desc(OpportunityCandidate.score), desc(OpportunityCandidate.created_at))
        ).all()
        approved = [candidate for candidate in candidates if candidate.status == "approved"]
        product_prompt = build_ruflo_product_prompt(_model_to_dict(approved[0])) if approved else None
        return templates.TemplateResponse(
            "opportunities.html",
            {
                "request": request,
                "candidates": candidates,
                "product_prompt": product_prompt,
                "kill_switch_active": is_kill_switch_active(),
            },
        )


@app.post("/opportunities/mock-scan")
def mock_scan():
    candidates = mock_candidates()
    inserted = 0
    skipped = 0
    with session_scope() as session:
        for candidate in candidates:
            exists = session.scalar(
                select(OpportunityCandidate.id).where(
                    OpportunityCandidate.source == candidate["source"],
                    OpportunityCandidate.topic == candidate["topic"],
                    OpportunityCandidate.vertical == candidate["vertical"],
                )
            )
            if exists:
                skipped += 1
                continue
            session.add(OpportunityCandidate(**candidate))
            inserted += 1
    return {"inserted": inserted, "skipped": skipped, "message": "Mock SIGNAL scan complete"}


@app.post("/opportunities/{candidate_id}/approve")
def approve_opportunity(candidate_id: int):
    """Approve an opportunity AND auto-create a prefilled draft product.

    Operator can edit title/format/notes/price before generation. This is the
    automation seam: the approval click should leave the operator with a
    populated draft, not a blank form.
    """
    with session_scope() as session:
        candidate = session.get(OpportunityCandidate, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        already_approved = candidate.status == "approved"
        if not already_approved:
            candidate.status = "approved"
            session.add(
                Approval(
                    entity_type="opportunity_candidate",
                    entity_id=candidate_id,
                    decision="approved",
                )
            )

        product = session.scalar(
            select(Product).where(Product.opportunity_id == candidate_id)
        )
        if product is None:
            defaults = build_default_product_fields(candidate)
            product = Product(
                opportunity_id=candidate_id,
                title=defaults["title"],
                production_format=defaults["production_format"],
                price=defaults["price"],
                notes=defaults["notes"],
                status="draft",
            )
            session.add(product)
            session.flush()  # populate product.id for redirect

        product_id = product.id

    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)


@app.get("/products")
def products(request: Request):
    with session_scope() as session:
        product_rows = session.scalars(select(Product).order_by(desc(Product.created_at))).all()
        approved_candidates = session.scalars(
            select(OpportunityCandidate).where(OpportunityCandidate.status == "approved").order_by(desc(OpportunityCandidate.score))
        ).all()
        listing_prompt = build_ruflo_listing_prompt(_model_to_dict(product_rows[0])) if product_rows else None
        return templates.TemplateResponse(
            "products.html",
            {
                "request": request,
                "products": product_rows,
                "approved_candidates": approved_candidates,
                "listing_prompt": listing_prompt,
            },
        )


@app.get("/products/{product_id}/edit")
def edit_product(request: Request, product_id: int):
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        artifacts = session.scalars(
            select(ProductArtifact)
            .where(ProductArtifact.product_id == product_id)
            .order_by(desc(ProductArtifact.created_at))
        ).all()
        files = session.scalars(
            select(ProductFile)
            .where(ProductFile.product_id == product_id)
            .order_by(desc(ProductFile.created_at))
        ).all()
        url_check = check_gumroad_url(product)
        return templates.TemplateResponse(
            "product_edit.html",
            {
                "request": request,
                "product": product,
                "artifacts": artifacts,
                "files": files,
                "statuses": PRODUCT_STATUSES,
                "url_check": url_check,
            },
        )


@app.post("/products/{product_id}/edit")
def update_product(
    product_id: int,
    title: str = Form(...),
    production_format: str = Form(""),
    price: Decimal = Form(Decimal("19")),
    status: str = Form("draft"),
    gumroad_url: str = Form(""),
    notes: str = Form(""),
):
    if status not in PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid product status")
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        product.title = title
        product.production_format = production_format
        product.price = price
        product.status = status
        product.gumroad_url = gumroad_url
        product.notes = notes
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)


@app.post("/products")
def create_product(
    opportunity_id: int = Form(...),
    title: str = Form(...),
    production_format: str = Form(""),
    price: Decimal = Form(Decimal("19")),
    notes: str = Form(""),
):
    with session_scope() as session:
        candidate = session.get(OpportunityCandidate, opportunity_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        product = Product(
            opportunity_id=opportunity_id,
            title=title,
            production_format=production_format or candidate.production_format,
            price=price,
            notes=notes,
            status="draft",
        )
        session.add(product)
    return RedirectResponse(url="/products", status_code=303)


@app.get("/products/{product_id}/artifacts/new")
def new_artifact(request: Request, product_id: int):
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return templates.TemplateResponse(
            "artifact_new.html",
            {
                "request": request,
                "product": product,
                "artifact_types": ARTIFACT_TYPES,
            },
        )


@app.post("/products/{product_id}/artifacts")
def create_artifact(
    product_id: int,
    artifact_type: str = Form(...),
    title: str = Form(""),
    content: str = Form(...),
    source: str = Form("ruflo"),
):
    if artifact_type not in ARTIFACT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact type")
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        session.add(
            ProductArtifact(
                product_id=product_id,
                artifact_type=artifact_type,
                title=title,
                content=content,
                source=source or "ruflo",
            )
        )
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)


@app.get("/revenue")
def revenue(request: Request):
    with session_scope() as session:
        events = session.scalars(select(RevenueEvent).order_by(desc(RevenueEvent.created_at))).all()
        products = session.scalars(select(Product).order_by(Product.title)).all()
        total = session.scalar(select(func.coalesce(func.sum(RevenueEvent.amount), 0))) or 0
        by_product_rows = session.execute(
            select(
                Product.id,
                Product.title,
                func.coalesce(func.sum(RevenueEvent.amount), 0).label("total"),
            )
            .outerjoin(RevenueEvent, RevenueEvent.product_id == Product.id)
            .group_by(Product.id, Product.title)
            .order_by(Product.title)
        ).all()
        return templates.TemplateResponse(
            "revenue.html",
            {
                "request": request,
                "events": events,
                "products": products,
                "total": total,
                "by_product_rows": by_product_rows,
            },
        )


@app.post("/revenue")
def create_revenue_event(
    product_id: int = Form(...),
    marketplace: str = Form("gumroad"),
    amount: Decimal = Form(...),
    currency: str = Form("USD"),
    event_type: str = Form("sale"),
    notes: str = Form(""),
):
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        session.add(
            RevenueEvent(
                product_id=product_id,
                marketplace=marketplace or "gumroad",
                amount=amount,
                currency=currency or "USD",
                event_type=event_type or "sale",
                notes=notes,
            )
        )
    return RedirectResponse(url="/revenue", status_code=303)


@app.get("/settings")
def settings(request: Request):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "kill_switch_active": is_kill_switch_active(),
            "daily_budget": get_daily_budget(),
        },
    )


@app.post("/settings/kill-switch")
def update_kill_switch(enabled: str = Form("false")):
    set_flag_value("hydra:kill", "true" if enabled == "true" else "false")
    return RedirectResponse(url="/settings", status_code=303)


@app.post("/settings/budget")
def update_budget(daily_budget_usd: Decimal = Form(...)):
    if daily_budget_usd < 0:
        raise HTTPException(status_code=400, detail="Budget cannot be negative")
    set_flag_value("daily_budget_usd", str(daily_budget_usd))
    return RedirectResponse(url="/settings", status_code=303)


def _model_to_dict(model) -> dict:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str, max_len: int = 40) -> str:
    if not value:
        return "untitled"
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    if not slug:
        return "untitled"
    return slug[:max_len].rstrip("-") or "untitled"


def _truncate_title(title: str, limit: int = 70) -> str:
    title = title.strip()
    if len(title) <= limit:
        return title
    return title[: limit - 3].rstrip() + "..."


_PRICE_HINTS = {
    "prompt pack": Decimal("9"),
    "cheat sheet": Decimal("9"),
    "printable": Decimal("9"),
    "checklist": Decimal("9"),
    "template bundle": Decimal("15"),
    "notion": Decimal("19"),
    "airtable": Decimal("19"),
    "workflow pdf": Decimal("15"),
    "script pack": Decimal("19"),
    "mini-toolkit": Decimal("29"),
    "toolkit": Decimal("29"),
}


def _suggest_price(production_format: str | None) -> Decimal:
    fmt = (production_format or "").lower()
    for hint, price in _PRICE_HINTS.items():
        if hint in fmt:
            return price
    return Decimal("19")


def build_default_product_fields(candidate: OpportunityCandidate) -> dict:
    """Deterministic prefill so 'Approve' lands the operator on a populated draft."""
    fmt = candidate.production_format or "digital pack"
    title = _truncate_title(f"{fmt.title()}: {candidate.topic}")
    score = candidate.score if candidate.score is not None else 0
    notes_lines = [
        f"Source: {candidate.source}",
        f"Vertical: {candidate.vertical}",
        f"Production format: {candidate.production_format}",
        f"SIGNAL score: {score}",
        "",
        "Evidence:",
        candidate.evidence or "(none)",
        "",
        "Suggested deliverable structure:",
        "- Promise / cover (1 page)",
        "- Quick-start (2-3 pages)",
        "- Core content (5-12 pages)",
        "- Templates / examples / prompts",
        "- Closing / cross-sell",
        "",
        "Operator notes:",
        "(edit before generation)",
    ]
    return {
        "title": title,
        "production_format": candidate.production_format,
        "price": _suggest_price(candidate.production_format),
        "notes": "\n".join(notes_lines),
    }


def check_gumroad_url(product: Product) -> dict | None:
    """Return a single warning/info dict for product_edit, or None if neutral."""
    url = (product.gumroad_url or "").strip()
    status = product.status or ""
    if status == "live" and not url:
        return {
            "level": "warning",
            "message": "Live status set without a Gumroad URL. Buyers cannot reach the listing.",
        }
    if url and not (url.startswith("http://") or url.startswith("https://")):
        return {
            "level": "warning",
            "message": "Gumroad URL must start with http:// or https://.",
        }
    if status == "live" and url:
        return {"level": "good", "message": "Launch URL ready."}
    return None


def _valid_basic_auth(auth_header: str, expected_user: str, expected_pass: str) -> bool:
    if not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header.removeprefix("Basic ").strip()).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        return False
    return secrets.compare_digest(username, expected_user) and secrets.compare_digest(password, expected_pass)


# ---------------------------------------------------------------------------
# Sprint 1.2 — file tracking, artifact export, HN collector, launch dashboard
# ---------------------------------------------------------------------------


@app.get("/products/{product_id}/files/new")
def new_product_file(request: Request, product_id: int):
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return templates.TemplateResponse(
            "product_files_new.html",
            {"request": request, "product": product},
        )


@app.post("/products/{product_id}/files")
def create_product_file(
    product_id: int,
    file_label: str = Form(...),
    file_path: str = Form(...),
    file_type: str = Form("manual"),
    notes: str = Form(""),
):
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        session.add(
            ProductFile(
                product_id=product_id,
                file_label=file_label,
                file_path=file_path,
                file_type=file_type or "manual",
                notes=notes,
            )
        )
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)


@app.post("/products/{product_id}/artifacts/export")
def export_product_artifacts(product_id: int):
    """Write every artifact for a product to exports/product_<id>/NNN_<type>_<slug>.md."""
    try:
        assert_system_can_act("artifact_export")
    except SystemActionBlocked as exc:
        return JSONResponse(
            {"blocked": True, "action": "artifact_export", "reason": str(exc)},
            status_code=423,
        )

    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        artifacts = session.scalars(
            select(ProductArtifact)
            .where(ProductArtifact.product_id == product_id)
            .order_by(ProductArtifact.created_at)
        ).all()
        product_title = product.title or f"product_{product_id}"
        rows = [
            {
                "id": a.id,
                "artifact_type": a.artifact_type,
                "title": a.title,
                "source": a.source,
                "content": a.content,
                "created_at": a.created_at.isoformat() if a.created_at else "",
            }
            for a in artifacts
        ]

    if not rows:
        return JSONResponse(
            {"product_id": product_id, "exported": [], "count": 0, "note": "No artifacts to export."},
        )

    export_dir = EXPORT_ROOT / f"product_{product_id}"
    export_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for index, row in enumerate(rows, start=1):
        slug = _slugify(row["title"] or row["artifact_type"])
        filename = f"{index:03d}_{row['artifact_type']}_{slug}.md"
        path = export_dir / filename
        body = (
            f"# {row['title'] or row['artifact_type']}\n\n"
            f"_Type: {row['artifact_type']} | Source: {row['source']} | "
            f"Created: {row['created_at']}_\n\n"
            f"_Product: {product_title} (id {product_id})_\n\n"
            f"---\n\n{row['content']}\n"
        )
        path.write_text(body, encoding="utf-8")
        written.append(str(path))

    return JSONResponse(
        {
            "product_id": product_id,
            "exported": written,
            "count": len(written),
            "directory": str(export_dir),
        }
    )


# ---- HackerNews collector --------------------------------------------------

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_DEFAULT_QUERY = "AI"
HN_MAX_HITS = 12


def _hn_demand_velocity(points: int, comments: int) -> float:
    raw = points * 1.2 + comments * 1.5
    return float(min(100.0, raw))


def _hn_to_candidate(hit: dict) -> dict | None:
    title = (hit.get("title") or "").strip()
    if not title:
        return None
    points = int(hit.get("points") or 0)
    comments = int(hit.get("num_comments") or 0)
    url = (hit.get("url") or "").strip()
    created = hit.get("created_at") or ""
    evidence = (
        f"HN story '{title}' with {points} points and {comments} comments "
        f"({created}). Link: {url or 'n/a'}"
    )
    candidate = {
        "source": "HackerNews",
        "topic": title[:200],
        "vertical": "AI tools",
        "production_format": "cheat sheet PDF",
        "demand_velocity": _hn_demand_velocity(points, comments),
        "monetization_fit": 60,
        "ai_exploitability": 75,
        "cross_source_confirmation": 30,  # single source — gates against premature acting
        "time_to_revenue": 70,
        "saturation_penalty": 30,
        "platform_risk_penalty": 20,
        "evidence": evidence,
    }
    candidate["score"] = calculate_score(candidate)
    return candidate


@app.post("/opportunities/collect/hn")
def collect_hn(query: str = Form(HN_DEFAULT_QUERY)):
    """Fetch recent HN stories matching `query` and seed candidates."""
    try:
        assert_system_can_act("collect_hn")
    except SystemActionBlocked as exc:
        return JSONResponse(
            {"blocked": True, "action": "collect_hn", "reason": str(exc)},
            status_code=423,
        )

    params = {"tags": "story", "query": query or HN_DEFAULT_QUERY}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(HN_SEARCH_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"HN fetch failed: {exc}") from exc

    hits = payload.get("hits", [])[:HN_MAX_HITS]
    candidates = [c for c in (_hn_to_candidate(h) for h in hits) if c]

    inserted = 0
    skipped = 0
    with session_scope() as session:
        for candidate in candidates:
            exists = session.scalar(
                select(OpportunityCandidate.id).where(
                    OpportunityCandidate.source == candidate["source"],
                    OpportunityCandidate.topic == candidate["topic"],
                    OpportunityCandidate.vertical == candidate["vertical"],
                )
            )
            if exists:
                skipped += 1
                continue
            session.add(OpportunityCandidate(**candidate))
            inserted += 1

    return {
        "source": "HackerNews",
        "query": query or HN_DEFAULT_QUERY,
        "fetched": len(hits),
        "scored": len(candidates),
        "inserted": inserted,
        "skipped": skipped,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


# ---- Launch dashboard ------------------------------------------------------


@app.get("/launch")
def launch_dashboard(request: Request):
    with session_scope() as session:
        approved_count = session.scalar(
            select(func.count(OpportunityCandidate.id)).where(
                OpportunityCandidate.status == "approved"
            )
        ) or 0
        products_count = session.scalar(select(func.count(Product.id))) or 0
        live_count = session.scalar(
            select(func.count(Product.id)).where(Product.status == "live")
        ) or 0

        missing_url_rows = session.scalars(
            select(Product)
            .where(Product.status.in_(("live", "listed")))
            .where(
                (Product.gumroad_url.is_(None)) | (func.trim(Product.gumroad_url) == "")
            )
            .order_by(desc(Product.created_at))
        ).all()

        total_revenue = session.scalar(
            select(func.coalesce(func.sum(RevenueEvent.amount), 0))
        ) or 0

        top_opportunities = session.scalars(
            select(OpportunityCandidate)
            .order_by(desc(OpportunityCandidate.score))
            .limit(5)
        ).all()
        latest_products = session.scalars(
            select(Product).order_by(desc(Product.created_at)).limit(5)
        ).all()

        return templates.TemplateResponse(
            "launch.html",
            {
                "request": request,
                "approved_count": approved_count,
                "products_count": products_count,
                "live_count": live_count,
                "missing_url_products": missing_url_rows,
                "missing_url_count": len(missing_url_rows),
                "total_revenue": total_revenue,
                "kill_switch_active": is_kill_switch_active(),
                "daily_budget": get_daily_budget(),
                "top_opportunities": top_opportunities,
                "latest_products": latest_products,
            },
        )
