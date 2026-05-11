"""
kit_routes.py — FastAPI router for ai_implementation_kit generation.
Sprint 2.2.

Wire into main.py with TWO lines near the top:
    from kit_routes import kit_router
    app.include_router(kit_router)

All LLM calls go through the existing guarded llm layer (imported from llm.py).
"""

import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

# These imports must match what your main.py already imports from db.py
from db import SessionLocal, Product, LlmCall

kit_router = APIRouter(prefix="/kits", tags=["kits"])

templates = Jinja2Templates(directory="templates")

PRODUCTS_ROOT = Path(os.getenv("HYDRA_PRODUCT_ROOT", Path(__file__).parent.parent / "products"))
KIT_THEME     = "real_estate"


# ── Helper: resolve llm caller ────────────────────────────────────────────────

def _get_llm_caller(db):
    """Return a kit-compatible LLM caller using the guarded call_llm_json layer.

    Sprint 2.3: wires make_kit_llm_caller(db) from kit_llm_adapter.py.
    All LLM spend flows through llm.py — no direct provider SDK calls.
    Returns None (deterministic fallback) only if the adapter import fails.
    """
    try:
        from kit_llm_adapter import make_kit_llm_caller
        caller = make_kit_llm_caller(db)
        logger.info("[kit_routes] LLM caller acquired: make_kit_llm_caller")
        return caller
    except ImportError as exc:
        logger.error(
            "[kit_routes] CRITICAL: kit_llm_adapter import failed — "
            "container may be running stale image. Rebuild required. Error: %s", exc
        )
        return None
    except Exception as exc:
        logger.error("[kit_routes] LLM adapter init failed: %s: %s", type(exc).__name__, exc)
        return None


def _flash_redirect(path: str, level: str, msg: str) -> RedirectResponse:
    qs = urlencode({"flash": level, "msg": msg})
    return RedirectResponse(f"{path}?{qs}", status_code=303)


# ── Routes ────────────────────────────────────────────────────────────────────

@kit_router.get("/{product_id}")
async def kit_detail(request: Request, product_id: int):
    """Kit status and management page for a product."""
    product_dir = PRODUCTS_ROOT / f"product_{product_id}"
    covers_dir  = product_dir / "covers"

    with SessionLocal() as session:
        product = session.get(Product, product_id)
        if not product:
            return HTMLResponse("<h1>Product not found</h1>", status_code=404)

    # Collect generated assets
    pdfs   = sorted(product_dir.glob("*.pdf"))   if product_dir.exists() else []
    htmls  = sorted(product_dir.glob("*.html"))  if product_dir.exists() else []
    covers = sorted(covers_dir.glob("*.svg"))     if covers_dir.exists() else []
    zip_f  = next(product_dir.glob("*.zip"), None) if product_dir.exists() else None

    flash = request.query_params.get("flash")
    msg   = request.query_params.get("msg", "")

    # Load last generation report if present
    report = None
    report_path = product_dir / "kit_generation_report.json"
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return templates.TemplateResponse("kit_status.html", {
        "request":     request,
        "product":     product,
        "product_dir": str(product_dir),
        "pdfs":        [p.name for p in pdfs],
        "htmls":       [h.name for h in htmls],
        "covers":      [c.name for c in covers],
        "zip_file":    zip_f.name if zip_f else None,
        "flash":       flash,
        "msg":         msg,
        "report":      report,
    })


@kit_router.post("/{product_id}/generate")
async def generate_kit_route(
    request: Request,
    product_id: int,
    kit_name:    str = Form(...),
    kit_tagline: str = Form(...),
    niche:       str = Form("Real Estate Agents"),
    niche_context: str = Form(""),
    kit_edition: str = Form("2026 Edition"),
    theme:       str = Form("real_estate"),
):
    """Trigger full kit generation for a product."""
    from kit_generator import generate_kit

    with SessionLocal() as session:
        product = session.get(Product, product_id)
        if not product:
            return _flash_redirect(f"/kits/{product_id}", "error", "Product not found")

        # Record deterministic kit generation in llm_calls for operator visibility.
        lc = LlmCall(
            provider="local",
            model="kit-generator",
            purpose="kit_generation",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0,
            status="started",
        )
        session.add(lc)
        session.commit()
        llm_call_id = lc.id

    try:
        started_at = time.monotonic()
        with SessionLocal() as generation_session:
            results = generate_kit(
                product_id=product_id,
                niche=niche,
                niche_context=niche_context or f"Professional real estate agents seeking AI implementation guidance",
                kit_name=kit_name,
                kit_tagline=kit_tagline,
                kit_edition=kit_edition,
                theme=theme,
                products_root=PRODUCTS_ROOT,
                llm_call_fn=_get_llm_caller(generation_session),
            )
            generation_session.commit()

        with SessionLocal() as session:
            lc = session.get(LlmCall, llm_call_id)
            if lc:
                lc.status = "success" if not results["errors"] else "completed_with_warnings"
                lc.duration_ms = int((time.monotonic() - started_at) * 1000)
                lc.error = "; ".join(results["errors"])[:1000] if results["errors"] else None
                lc.error_type = "kit_generation_warning" if results["errors"] else None
                session.commit()

        pdf_count = len(results["pdfs"])
        err_count = len(results["errors"])
        llm_used  = results.get("llm_used", False)
        fallback  = results.get("fallback_docs", [])
        if llm_used and not fallback:
            msg = f"Kit generated: {pdf_count} PDFs — LLM content ✓"
        elif llm_used and fallback:
            msg = f"Kit generated: {pdf_count} PDFs — LLM partial ({len(fallback)} docs used fallback)"
        else:
            msg = f"Kit generated: {pdf_count} PDFs — FALLBACK ONLY (no LLM content)"
        if err_count:
            msg += f" | {err_count} error(s) — check logs"
        level = "success" if llm_used else "warning"
        return _flash_redirect(f"/kits/{product_id}", level, msg)

    except Exception as e:
        with SessionLocal() as session:
            lc = session.get(LlmCall, llm_call_id)
            if lc:
                lc.status = "failed"
                lc.error = str(e)[:1000]
                lc.error_type = "kit_generation_failed"
                session.commit()
        return _flash_redirect(
            f"/kits/{product_id}", "error", f"Generation failed: {str(e)[:120]}"
        )


@kit_router.post("/{product_id}/covers")
async def generate_covers_only(request: Request, product_id: int):
    """Generate/regenerate only the SVG covers (fast, no LLM)."""
    from kit_covers import build_kit_covers

    kit_name    = request.query_params.get("kit_name", "Real Estate AI Mastery Kit")
    kit_tagline = request.query_params.get("kit_tagline", "The complete AI implementation system for modern agents")
    theme       = request.query_params.get("theme", "real_estate")

    product_dir = PRODUCTS_ROOT / f"product_{product_id}"
    covers = build_kit_covers(
        product_dir=product_dir,
        kit_name=kit_name,
        kit_tagline=kit_tagline,
        theme=theme,
    )
    return _flash_redirect(
        f"/kits/{product_id}", "success", f"{len(covers)} SVG covers generated"
    )


@kit_router.get("/{product_id}/download/{filename}")
async def download_kit_file(product_id: int, filename: str):
    """Serve a generated kit file (PDF, ZIP, SVG cover) for download."""
    # Security: filename must not escape product_dir
    product_dir = PRODUCTS_ROOT / f"product_{product_id}"
    safe_name   = Path(filename).name  # strip any path traversal

    # Check in root and covers/
    for candidate in [product_dir / safe_name, product_dir / "covers" / safe_name]:
        if candidate.exists() and candidate.is_file():
            media = "application/zip" if safe_name.endswith(".zip") else \
                    "image/svg+xml"   if safe_name.endswith(".svg") else \
                    "application/pdf"
            return FileResponse(
                path=str(candidate),
                filename=safe_name,
                media_type=media,
            )

    return HTMLResponse("<h1>File not found</h1>", status_code=404)


@kit_router.post("/{product_id}/delete")
async def delete_kit(request: Request, product_id: int):
    """Delete generated kit assets for a product without removing other packages."""
    import shutil
    product_dir = PRODUCTS_ROOT / f"product_{product_id}"
    if product_dir.exists():
        for pattern in ("*.html", "*.pdf", "*.zip"):
            for path in product_dir.glob(pattern):
                if path.is_file():
                    path.unlink()
        covers_dir = product_dir / "covers"
        if covers_dir.exists():
            shutil.rmtree(covers_dir)
    return _flash_redirect(
        f"/products/{product_id}/edit", "success", "Kit assets deleted"
    )
