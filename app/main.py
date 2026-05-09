from __future__ import annotations

import base64
import json
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
    LlmCall,
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
from llm import LlmBlocked, LlmFailed, call_llm_json, get_today_llm_spend
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
            defaults = build_default_product_fields(candidate, session)
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
        generation_steps = ("outline", "product_content", "listing_copy", "qa_review", "distribution_post")
        generation_status = {
            step: _latest_artifact(session, product_id, step)
            for step in generation_steps
        }
        return templates.TemplateResponse(
            "product_edit.html",
            {
                "request": request,
                "product": product,
                "artifacts": artifacts,
                "files": files,
                "statuses": PRODUCT_STATUSES,
                "url_check": url_check,
                "generation_status": generation_status,
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
    source_attribution: str = Form(""),
    channel_tag: str = Form(""),
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
                source_attribution=(source_attribution or "").strip() or None,
                channel_tag=(channel_tag or "").strip().lower() or None,
            )
        )
    return RedirectResponse(url="/revenue", status_code=303)


@app.get("/settings")
def settings(request: Request):
    with session_scope() as session:
        recent_llm_calls = session.scalars(
            select(LlmCall).order_by(desc(LlmCall.created_at)).limit(8)
        ).all()
        today_llm_spend = get_today_llm_spend(session)
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "kill_switch_active": is_kill_switch_active(),
                "daily_budget": get_daily_budget(),
                "today_llm_spend": today_llm_spend,
                "recent_llm_calls": recent_llm_calls,
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


def _format_short_label(production_format: str | None) -> str:
    """Human-friendly format label for titles. Avoids `'cheat sheet PDF'.title()` ugliness."""
    if not production_format:
        return "Pack"
    f = production_format.lower()
    pairs = (
        ("cheat sheet", "Cheat Sheet"),
        ("prompt pack", "Prompt Pack"),
        ("notion", "Notion Template"),
        ("airtable", "Airtable Template"),
        ("checklist", "Checklist"),
        ("printable", "Printable Pack"),
        ("template bundle", "Template Bundle"),
        ("workflow pdf", "Workflow Guide"),
        ("workflow guide", "Workflow Guide"),
        ("script pack", "Script Pack"),
        ("mini-toolkit", "Toolkit"),
        ("toolkit", "Toolkit"),
        ("planner", "Planner"),
        ("tracker", "Tracker"),
        ("kit", "Kit"),
        ("guide", "Guide"),
        ("pdf", "Guide"),
    )
    for needle, label in pairs:
        if needle in f:
            return label
    return "Pack"


def build_default_product_fields(candidate: OpportunityCandidate, db=None) -> dict:
    """Prefill a draft product, using LLM notes only when guarded calls succeed."""
    short = _format_short_label(candidate.production_format)
    title = _truncate_title(f"{candidate.topic} — {short}")
    notes = _build_llm_product_notes(candidate, db) if db is not None else None
    if notes is None:
        notes = _build_deterministic_product_notes(candidate)
    return {
        "title": title,
        "production_format": candidate.production_format,
        "price": _suggest_price(candidate.production_format),
        "notes": notes,
    }


def _build_deterministic_product_notes(candidate: OpportunityCandidate) -> str:
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
    return "\n".join(notes_lines)


def _build_llm_product_notes(candidate: OpportunityCandidate, db) -> str | None:
    schema = {
        "product_angle": "string",
        "target_buyer": "string",
        "pain_point": "string",
        "suggested_deliverables": ["string"],
        "distribution_angle": "string",
        "risk_notes": "string",
    }
    system_prompt = (
        "You are HYDRA Zone B support code. Produce operator-editable product draft notes only. "
        "Do not write final product content. Do not claim legal, medical, political, or financial advice."
    )
    user_prompt = (
        f"Topic: {candidate.topic}\n"
        f"Source: {candidate.source}\n"
        f"Vertical: {candidate.vertical}\n"
        f"Production format: {candidate.production_format}\n"
        f"Evidence: {candidate.evidence or '(none)'}\n\n"
        "Return concise structured notes with product angle, target buyer, pain point, suggested deliverables, "
        "distribution angle, and risk notes."
    )
    try:
        data = call_llm_json(
            db,
            purpose="product_prefill",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_hint=schema,
            max_cost_usd=0.001,
            timeout_seconds=20,
        )
    except (LlmBlocked, LlmFailed):
        return None

    deliverables = data.get("suggested_deliverables") or []
    if not isinstance(deliverables, list):
        deliverables = [str(deliverables)]
    lines = [
        "LLM-assisted draft notes (operator must review):",
        f"Product angle: {str(data.get('product_angle') or '').strip()}",
        f"Target buyer: {str(data.get('target_buyer') or '').strip()}",
        f"Pain point: {str(data.get('pain_point') or '').strip()}",
        "Suggested deliverables:",
    ]
    lines.extend(f"- {str(item).strip()}" for item in deliverables[:8] if str(item).strip())
    lines.extend(
        [
            f"Distribution angle: {str(data.get('distribution_angle') or '').strip()}",
            f"Risk notes: {str(data.get('risk_notes') or 'None noted').strip()}",
            "",
            "Operator notes:",
            "(edit before generation)",
        ]
    )
    return "\n".join(lines)


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
    pairs: list[tuple[str, str, str]] = []  # (label, path, type)
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
        pairs.append((filename, str(path), "export"))

    # Auto-register product_files rows so the operator never loses track of where
    # an artifact landed on disk. Idempotent via the (product_id, file_path) unique
    # index applied in db._apply_one_shot_migrations().
    registered = 0
    with session_scope() as session:
        for label, path_str, ftype in pairs:
            exists = session.scalar(
                select(ProductFile.id).where(
                    ProductFile.product_id == product_id,
                    ProductFile.file_path == path_str,
                )
            )
            if exists:
                continue
            session.add(
                ProductFile(
                    product_id=product_id,
                    file_label=label,
                    file_path=path_str,
                    file_type=ftype,
                    notes="auto-registered by artifact export",
                )
            )
            registered += 1

    return JSONResponse(
        {
            "product_id": product_id,
            "exported": written,
            "count": len(written),
            "directory": str(export_dir),
            "files_registered": registered,
        }
    )


# ---- HackerNews collector --------------------------------------------------

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_DEFAULT_QUERY = "AI"
HN_MAX_HITS = 12


def _hn_demand_velocity(points: int, comments: int) -> float:
    raw = points * 1.2 + comments * 1.5
    return float(min(100.0, raw))


# Sprint 1.3 — keyword-based classifier. NO LLM. Order matters: more specific first.
_HN_RULES: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("agent", "copilot", "cursor", "claude code", "cline", "codex", "aider", "devin"),
     "AI coding tools", "cheat sheet PDF"),
    (("rag ", "retrieval augmented", "vector db", "embedding", "pgvector"),
     "AI infrastructure", "cheat sheet PDF"),
    (("llm", "language model", " gpt", " gpt-", "chatgpt", "claude ", " claude.", "gemini", "anthropic", "openai"),
     "AI tools", "prompt pack"),
    (("kubernetes", "k8s", "terraform", "ansible", "ci/cd", "github actions", "devops", "sre "),
     "DevOps", "cheat sheet PDF"),
    (("postgres", "sqlite", "mysql", "mariadb", "duckdb", "database", " sql ", "sqlalchemy"),
     "Databases", "cheat sheet PDF"),
    (("react", "next.js", "nextjs", "vue", "svelte", "tailwind", "frontend"),
     "Frontend", "cheat sheet PDF"),
    (("rust", "golang", "go ", "python", "typescript", "deno", "bun"),
     "Programming languages", "prompt pack"),
    (("security", "vulnerability", "exploit", "infosec", "cve", "pentest"),
     "Security", "checklist PDF"),
    (("startup", " yc ", " y combinator", "founder", "saas", "indie hackers"),
     "Startup playbooks", "Notion template"),
    (("homelab", "self-host", "selfhosted", "self host"),
     "Homelab", "cheat sheet PDF"),
    (("notion", "obsidian", "logseq"),
     "Knowledge management", "Notion template"),
)


def _hn_classify_rules(title: str) -> tuple[str, str]:
    """Return (vertical, production_format). Falls back to AI tools / cheat sheet PDF."""
    t = title.lower()
    for needles, vertical, fmt in _HN_RULES:
        if any(n in t for n in needles):
            return vertical, fmt
    return "AI tools", "cheat sheet PDF"


def _hn_classify(title: str, snippet: str = "", db=None):
    """Classify HN story. LLM attempts fall back to the Sprint 1.3 keyword router."""
    if db is None:
        vertical, fmt = _hn_classify_rules(title)
        return vertical, fmt

    schema = {
        "vertical": "AI coding tools",
        "production_format": "cheat sheet PDF",
        "topic_normalized": "Safe AI Coding Agent Workflow",
        "monetization_angle": "rollback workflows and prompt guardrails for developers",
        "risk_flags": ["none"],
    }
    system_prompt = (
        "Given a HackerNews story title and snippet, classify the buyer audience and best digital-product format. "
        "Return strict JSON only. Do not recommend political, medical, financial, or legal advice products unless "
        "risk_flags names the risk. Do not suggest trademark-copying products."
    )
    user_prompt = f"Title: {title}\nSnippet: {snippet or '(none)'}"
    try:
        data = call_llm_json(
            db,
            purpose="hn_classification",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_hint=schema,
            max_cost_usd=0.0005,
            timeout_seconds=20,
        )
        vertical = str(data.get("vertical") or "").strip()
        fmt = str(data.get("production_format") or "").strip()
        if not vertical or not fmt:
            raise ValueError("Missing vertical or production_format")
        risk_flags = data.get("risk_flags")
        if _looks_like_regulated_advice(vertical, title) and not risk_flags:
            data["risk_flags"] = ["regulated-advice-risk"]
        return vertical[:80], fmt[:80], data
    except (LlmBlocked, LlmFailed, ValueError):
        vertical, fmt = _hn_classify_rules(title)
        return vertical, fmt, None


def _looks_like_regulated_advice(vertical: str, title: str) -> bool:
    text = f"{vertical} {title}".lower()
    return any(
        word in text
        for word in ("medical", "health", "legal", "law", "financial", "invest", "political")
    )


def _hn_to_candidate(hit: dict, db=None) -> dict | None:
    title = (hit.get("title") or "").strip()
    if not title:
        return None
    points = int(hit.get("points") or 0)
    comments = int(hit.get("num_comments") or 0)
    url = (hit.get("url") or "").strip()
    created = hit.get("created_at") or ""
    snippet = (hit.get("story_text") or hit.get("comment_text") or "").strip()
    classified = _hn_classify(title, snippet, db)
    if len(classified) == 2:
        vertical, production_format = classified
        llm_meta = None
    else:
        vertical, production_format, llm_meta = classified
    evidence = (
        f"HN story '{title}' with {points} points and {comments} comments "
        f"({created}). Link: {url or 'n/a'}. Classified as {vertical} / {production_format}."
    )
    if llm_meta:
        evidence += (
            f" LLM normalized topic: {llm_meta.get('topic_normalized', 'n/a')}. "
            f"Monetization angle: {llm_meta.get('monetization_angle', 'n/a')}. "
            f"Risk flags: {', '.join(llm_meta.get('risk_flags') or ['none'])}."
        )
    candidate = {
        "source": "HackerNews",
        "topic": title[:200],
        "vertical": vertical,
        "production_format": production_format,
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
    inserted = 0
    skipped = 0
    with session_scope() as session:
        candidates = [c for c in (_hn_to_candidate(h, session) for h in hits) if c]
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

        # Sprint 1.3 — channel rollup (revenue grouped by channel_tag).
        # Group by the raw column; coalesce NULL → "(unattributed)" only in SELECT.
        channel_rows_raw = session.execute(
            select(
                RevenueEvent.channel_tag,
                func.coalesce(func.sum(RevenueEvent.amount), 0).label("total"),
                func.count(RevenueEvent.id).label("events"),
            )
            .group_by(RevenueEvent.channel_tag)
            .order_by(desc("total"))
        ).all()
        channel_rows = [
            {"channel": (row.channel_tag or "(unattributed)"),
             "total": row.total,
             "events": row.events}
            for row in channel_rows_raw
        ]

        # Sprint 1.3 — live products that have no published distribution post.
        # Subquery: product_ids that DO have at least one published distribution_post.
        published_product_ids = session.scalars(
            select(ProductArtifact.product_id)
            .where(ProductArtifact.artifact_type == "distribution_post")
            .where(ProductArtifact.published_url.is_not(None))
            .where(ProductArtifact.published_url != "")
            .distinct()
        ).all()
        missing_distribution = session.scalars(
            select(Product)
            .where(Product.status == "live")
            .where(~Product.id.in_(published_product_ids) if published_product_ids else True)
            .order_by(desc(Product.created_at))
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
                "missing_distribution": missing_distribution,
                "missing_distribution_count": len(missing_distribution),
                "channel_rows": channel_rows,
                "total_revenue": total_revenue,
                "kill_switch_active": is_kill_switch_active(),
                "daily_budget": get_daily_budget(),
                "top_opportunities": top_opportunities,
                "latest_products": latest_products,
            },
        )


# ---------------------------------------------------------------------------
# Sprint 1.3 — distribution publish tracking
# ---------------------------------------------------------------------------


@app.post("/products/{product_id}/artifacts/{artifact_id}/publish")
def mark_artifact_published(
    product_id: int,
    artifact_id: int,
    published_url: str = Form(...),
    channel_tag: str = Form(""),
):
    """Record that a distribution_post artifact has been published in a channel."""
    url = (published_url or "").strip()
    if url and not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(
            status_code=400,
            detail="published_url must start with http:// or https://",
        )
    with session_scope() as session:
        artifact = session.get(ProductArtifact, artifact_id)
        if not artifact or artifact.product_id != product_id:
            raise HTTPException(status_code=404, detail="Artifact not found")
        artifact.published_url = url or None
        artifact.published_at = datetime.utcnow() if url else None
        artifact.channel_tag = (channel_tag or "").strip().lower() or None
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)

# ---------------------------------------------------------------------------
# Sprint 1.5 — In-process agentic generation (multi-marketplace aware)
# ---------------------------------------------------------------------------
# Philosophy: all generation flows through the guarded app/llm.py client.
# Each route saves one ProductArtifact. Human reviews and advances each step.
# No publishing, no auto-spending beyond budget-capped LLM calls.
# Target marketplaces from day one: Gumroad, Etsy, Sellfy, Payhip.
# ---------------------------------------------------------------------------

_STEP_REQUIRES: dict[str, str | None] = {
    "outline":           None,
    "product_content":   "outline",
    "listing_copy":      "product_content",
    "qa_review":         "product_content",
    "distribution_post": "listing_copy",
}


def _latest_artifact(session, product_id: int, artifact_type: str):
    """Return the most recent artifact of the given type, or None."""
    return session.scalar(
        select(ProductArtifact)
        .where(ProductArtifact.product_id == product_id)
        .where(ProductArtifact.artifact_type == artifact_type)
        .order_by(desc(ProductArtifact.created_at))
    )


def _generation_error(action: str, status: str, message: str) -> JSONResponse:
    return JSONResponse({"status": status, "action": action, "message": message})


def _artifact_context(session, product_id: int, artifact_type: str) -> dict:
    """Parse latest artifact JSON of given type; return {} on miss or decode error."""
    art = _latest_artifact(session, product_id, artifact_type)
    if not art:
        return {}
    try:
        return json.loads(art.content)
    except (json.JSONDecodeError, ValueError):
        return {}


@app.post("/products/{product_id}/generate/outline")
def generate_outline(product_id: int):
    """Step 1: generate a multi-marketplace product outline from the opportunity signal."""
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        candidate = session.get(OpportunityCandidate, product.opportunity_id) if product.opportunity_id else None

        schema = {
            "product_title": "string",
            "tagline": "string",
            "buyer_persona": "string",
            "core_pain_solved": "string",
            "deliverable_sections": [
                {"title": "string", "purpose": "string", "estimated_length": "string"}
            ],
            "etsy_keyword_angle": "string",
            "gumroad_hook": "string",
            "risk_notes": "none",
        }
        system_prompt = (
            "You are HYDRA's Product Architect. Produce a commercially-focused digital download outline "
            "targeting Gumroad, Etsy, Sellfy, and Payhip buyers simultaneously. Return strict JSON only. "
            "The product must be a standalone download — no upsells or sign-up walls. "
            "Do not recommend medical, legal, financial, or political advice without flagging risk_notes. "
            "Do not imitate or copy copyrighted properties."
        )
        evidence = (candidate.evidence if candidate else None) or product.notes or "(none)"
        user_prompt = (
            f"Topic: {product.title}\n"
            f"Vertical: {candidate.vertical if candidate else 'general'}\n"
            f"Production format: {product.production_format or 'digital download'}\n"
            f"Price target: ${product.price}\n"
            f"Target marketplaces: Gumroad, Etsy, Sellfy, Payhip\n"
            f"Signal evidence: {evidence}\n\n"
            "deliverable_sections: 4-8 items. "
            "etsy_keyword_angle: one sentence on the SEO keyword angle for Etsy title and tags. "
            "gumroad_hook: one sentence opening hook for the Gumroad/Sellfy description. "
            "risk_notes: 'none' or a description of any IP, legal, or platform-policy risk."
        )
        try:
            data = call_llm_json(session, "outline", system_prompt, user_prompt, schema, max_cost_usd=0.003)
            session.add(ProductArtifact(
                product_id=product_id,
                artifact_type="outline",
                title=f"Outline: {data.get('product_title', product.title)}",
                content=json.dumps(data, indent=2),
                source="hydra-llm:outline",
            ))
        except (LlmBlocked, LlmFailed) as exc:
            return _generation_error("outline", "blocked" if isinstance(exc, LlmBlocked) else "failed", str(exc))
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)


@app.post("/products/{product_id}/generate/content")
def generate_content(product_id: int):
    """Step 2: write complete buyer-ready content for every section in the outline."""
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if not _latest_artifact(session, product_id, "outline"):
            return _generation_error("content", "missing_prereq", "Generate and review an Outline first.")

        outline = _artifact_context(session, product_id, "outline")
        sections = outline.get("deliverable_sections") or []
        sections_text = "\n".join(
            f"- {s.get('title', 'Section')}: {s.get('purpose', '')} ({s.get('estimated_length', '')})"
            for s in sections
        ) or "(no sections in outline — regenerate outline)"

        schema = {
            "sections": [{"title": "string", "content": "string"}],
            "total_word_count_estimate": 0,
        }
        system_prompt = (
            "You are HYDRA's Product Writer. Write complete, buyer-ready content for every section listed. "
            "This is a finished product — not a draft, skeleton, or template with blanks. "
            "Every section must be fully written. Never write placeholder text like [INSERT HERE]. "
            "Do not include medical, legal, financial, or political advice. Return strict JSON only."
        )
        user_prompt = (
            f"Product title: {product.title}\n"
            f"Production format: {product.production_format or 'digital download'}\n"
            f"Buyer persona: {outline.get('buyer_persona', 'buyer')}\n"
            f"Core pain solved: {outline.get('core_pain_solved', '')}\n"
            f"Target marketplaces: Gumroad, Etsy, Sellfy, Payhip\n\n"
            f"Sections to write:\n{sections_text}\n\n"
            "Return one JSON object per section with its full written content. Aim for publication quality."
        )
        try:
            data = call_llm_json(session, "product_content", system_prompt, user_prompt, schema, max_cost_usd=0.012)
            session.add(ProductArtifact(
                product_id=product_id,
                artifact_type="product_content",
                title=f"Content: {product.title}",
                content=json.dumps(data, indent=2),
                source="hydra-llm:content",
            ))
        except (LlmBlocked, LlmFailed) as exc:
            return _generation_error("content", "blocked" if isinstance(exc, LlmBlocked) else "failed", str(exc))
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)


@app.post("/products/{product_id}/generate/listing")
def generate_listing(product_id: int):
    """Step 3: generate platform-optimized listing copy for all four storefronts."""
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if not _latest_artifact(session, product_id, "product_content"):
            return _generation_error("listing", "missing_prereq", "Generate Content first.")

        outline = _artifact_context(session, product_id, "outline")
        content_data = _artifact_context(session, product_id, "product_content")
        sections = content_data.get("sections") or []
        content_preview = " ".join(
            s.get("content", "")[:400] for s in sections[:3]
        )[:1000]

        schema = {
            "gumroad": {"title": "string", "description": "string", "tags": ["string"]},
            "etsy": {
                "title": "string",
                "description": "string",
                "tags": ["string"] * 13,
                "category_hint": "string",
            },
            "sellfy": {"title": "string", "description": "string"},
            "payhip": {"title": "string", "description": "string"},
            "universal": {"short_description": "string", "tagline": "string"},
        }
        system_prompt = (
            "You are HYDRA's Marketplace Copywriter specializing in digital downloads sold across multiple storefronts. "
            "Rules by platform:\n"
            "Gumroad: title 60-80 chars, description 300-600 words, conversational and benefit-led, tags optional.\n"
            "Etsy: title MUST be under 140 chars starting with the primary search keyword buyers type; "
            "exactly 13 tags each under 20 chars, comma-separated, covering every keyword angle; "
            "description 400-600 words, keyword-rich, explains what buyer gets, format, and primary use cases.\n"
            "Sellfy: title under 80 chars, description 200-350 words, punchy and conversion-focused.\n"
            "Payhip: title under 80 chars, description 200-300 words, friendly and benefit-first.\n"
            "universal.short_description: under 160 chars, usable as a tweet or meta description.\n"
            "Do not fabricate reviews, statistics, or credentials. No medical/legal/financial advice. "
            "Return strict JSON only."
        )
        user_prompt = (
            f"Product title: {product.title}\n"
            f"Production format: {product.production_format or 'digital download'}\n"
            f"Price: ${product.price}\n"
            f"Buyer persona: {outline.get('buyer_persona', '')}\n"
            f"Core pain solved: {outline.get('core_pain_solved', '')}\n"
            f"Tagline: {outline.get('tagline', '')}\n"
            f"Etsy keyword angle: {outline.get('etsy_keyword_angle', '')}\n"
            f"Gumroad hook: {outline.get('gumroad_hook', '')}\n"
            f"Content preview: {content_preview}\n\n"
            "Generate listing copy for all four storefronts plus universal fields."
        )
        try:
            data = call_llm_json(session, "listing_copy", system_prompt, user_prompt, schema, max_cost_usd=0.006)
            session.add(ProductArtifact(
                product_id=product_id,
                artifact_type="listing_copy",
                title=f"Listing Copy (Gumroad + Etsy + Sellfy + Payhip): {product.title}",
                content=json.dumps(data, indent=2),
                source="hydra-llm:listing",
            ))
        except (LlmBlocked, LlmFailed) as exc:
            return _generation_error("listing", "blocked" if isinstance(exc, LlmBlocked) else "failed", str(exc))
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)


@app.post("/products/{product_id}/generate/qa")
def generate_qa(product_id: int):
    """Step 4: adversarial QA review using the alternate provider as critic."""
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if not _latest_artifact(session, product_id, "product_content"):
            return _generation_error("qa", "missing_prereq", "Generate Content first.")

        content_data = _artifact_context(session, product_id, "product_content")
        listing_data = _artifact_context(session, product_id, "listing_copy")
        sections = content_data.get("sections") or []
        content_preview = "\n\n".join(
            f"## {s.get('title', '')}\n{s.get('content', '')[:700]}"
            for s in sections[:4]
        )[:2500]
        gumroad_desc = (listing_data.get("gumroad") or {}).get("description", "")[:800]
        etsy_title = (listing_data.get("etsy") or {}).get("title", "")
        etsy_tags = (listing_data.get("etsy") or {}).get("tags", [])

        schema = {
            "score": 0,
            "publishable": True,
            "blocking_issues": ["string"],
            "non_blocking_suggestions": ["string"],
            "slop_phrases_found": ["string"],
            "risk_flags": ["string"],
            "etsy_tag_issues": ["string"],
        }
        system_prompt = (
            "You are an adversarial quality reviewer for a digital download marketplace seller. "
            "Buyers paid real money. Be skeptical and specific. Never be generous out of politeness. "
            "Score: 90+ = publish-ready; 70-89 = publishable with minor edits; below 70 = revise first. "
            "publishable: true only if score >= 70 AND no blocking issues. Return strict JSON only."
        )
        etsy_tag_text = ", ".join(etsy_tags) if etsy_tags else "(no tags generated)"
        user_prompt = (
            f"Product title: {product.title}\n"
            f"Production format: {product.production_format or 'digital download'}\n"
            f"Price: ${product.price}\n\n"
            f"Content (first 4 sections):\n{content_preview}\n\n"
            f"Gumroad description:\n{gumroad_desc}\n\n"
            f"Etsy title: {etsy_title}\n"
            f"Etsy tags: {etsy_tag_text}\n\n"
            "Evaluate: (1) title vs content match, (2) hallucinated facts or tool names, "
            "(3) incomplete/skeleton sections, (4) AI slop phrases, "
            "(5) IP/trademark/regulated-advice risks, (6) Gumroad listing honestly represents the product, "
            "(7) Etsy title starts with primary keyword and is under 140 chars, "
            "(8) Etsy tags: exactly 13, each under 20 chars, no duplicates. "
            "List every blocking issue separately in blocking_issues."
        )
        try:
            # QA uses reverse_providers so it critiques with the alternate model family
            data = call_llm_json(
                session, "qa_review", system_prompt, user_prompt, schema,
                max_cost_usd=0.006, reverse_providers=True,
            )
            score = data.get("score", 0)
            publishable = data.get("publishable", False)
            session.add(ProductArtifact(
                product_id=product_id,
                artifact_type="qa_review",
                title=f"QA Review (score={score}, publishable={publishable}): {product.title}",
                content=json.dumps(data, indent=2),
                source="hydra-llm:qa",
            ))
        except (LlmBlocked, LlmFailed) as exc:
            return _generation_error("qa", "blocked" if isinstance(exc, LlmBlocked) else "failed", str(exc))
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)


@app.post("/products/{product_id}/generate/distribution")
def generate_distribution(product_id: int):
    """Step 5: generate platform-native launch posts across Reddit, X, HN, IndieHackers."""
    with session_scope() as session:
        product = session.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if not _latest_artifact(session, product_id, "listing_copy"):
            return _generation_error("distribution", "missing_prereq", "Generate Listing Copy first.")

        outline = _artifact_context(session, product_id, "outline")
        listing_data = _artifact_context(session, product_id, "listing_copy")
        universal = listing_data.get("universal") or {}
        gumroad_url = (product.gumroad_url or "").strip() or "TBD — add Gumroad URL to product before posting"

        schema = {
            "reddit": {
                "suggested_subreddits": ["string"],
                "title": "string",
                "body": "string",
            },
            "twitter_x": {
                "thread_hook": "string",
                "thread_body": "string",
            },
            "hn_show_hn": {
                "title": "string",
                "comment": "string",
            },
            "indiehackers": {
                "title": "string",
                "body": "string",
            },
            "operator_notes": "string",
        }
        system_prompt = (
            "You are HYDRA's Distribution Writer. Write launch posts for digital products that feel "
            "completely native to each platform. Lead with value, never with the product itself. "
            "You are a real person sharing something genuinely useful — not a marketer.\n"
            "Reddit: add real value first; mention the product softly at the end; link as postscript. "
            "Suggest 2-3 specific subreddits where this exact audience lives.\n"
            "Twitter/X: thread_hook under 280 chars (strong hook that stands alone); "
            "thread_body 2-4 follow-up tweets separated by a blank line.\n"
            "HN Show HN: title as 'Show HN: ...' with technical framing; honest, no hype; "
            "comment provides context and link.\n"
            "IndieHackers: builder story angle — what you noticed, what you built, what you learned; "
            "community-first, link at the end.\n"
            "operator_notes: one sentence of platform-specific advice the human should remember before posting.\n"
            "NEVER write fake social proof, engagement-bait, or fabricated statistics. "
            "Return strict JSON only."
        )
        user_prompt = (
            f"Product title: {product.title}\n"
            f"Tagline: {universal.get('short_description', outline.get('tagline', ''))}\n"
            f"Production format: {product.production_format or 'digital download'}\n"
            f"Buyer persona: {outline.get('buyer_persona', '')}\n"
            f"Core pain solved: {outline.get('core_pain_solved', '')}\n"
            f"Gumroad URL: {gumroad_url}\n\n"
            "Generate platform-specific launch posts. The operator will review and post manually. "
            "No post should be copy-pasted across platforms — each must be rewritten for its audience."
        )
        try:
            data = call_llm_json(
                session, "distribution_post", system_prompt, user_prompt, schema, max_cost_usd=0.006
            )
            session.add(ProductArtifact(
                product_id=product_id,
                artifact_type="distribution_post",
                title=f"Distribution Posts (Reddit / X / HN / IH): {product.title}",
                content=json.dumps(data, indent=2),
                source="hydra-llm:distribution",
            ))
        except (LlmBlocked, LlmFailed) as exc:
            return _generation_error("distribution", "blocked" if isinstance(exc, LlmBlocked) else "failed", str(exc))
    return RedirectResponse(url=f"/products/{product_id}/edit", status_code=303)
