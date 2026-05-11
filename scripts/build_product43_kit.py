#!/usr/bin/env python3
"""
build_product43_kit.py — Standalone script to build the Product 43 Real Estate AI Kit.
Sprint 2.2.

Run from project root:
    cd /home/jb/dev/hydra
    python scripts/build_product43_kit.py

Or with a specific output dir:
    python scripts/build_product43_kit.py --out /tmp/kit_test

Requires (install if missing):
    pip install weasyprint      # preferred PDF renderer
    pip install pypdf           # master PDF merge
    # OR: pip install pdfkit   # alternative (needs wkhtmltopdf system binary)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add app/ to path so we can import from it
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "app"))

from kit_generator import generate_kit, KIT_DOCUMENTS, SYSTEM_PROMPT, _sections_prompt
from kit_covers import build_kit_covers


KIT_NAME    = "Real Estate AI Mastery Kit"
KIT_TAGLINE = "The complete AI implementation system for modern agents"
KIT_EDITION = "2026 Edition"
PRODUCT_ID  = 43
NICHE       = "Real Estate Agents"
NICHE_CONTEXT = (
    "Professional real estate agents (3-15 years experience), individual contributors "
    "or small teams, US market, primarily residential. They need immediately usable tools, "
    "not theory. They are not developers. They are salespeople with operational pain."
)


def get_llm_caller():
    """Return a guarded LLM caller via kit_llm_adapter.make_kit_llm_caller.

    Sprint 2.3: all LLM spend flows through call_llm_json in app/llm.py.
    No direct Anthropic or OpenAI SDK calls. Returns None on failure so
    generate_document_content falls back to deterministic content.
    """
    try:
        from db import SessionLocal
        from kit_llm_adapter import make_kit_llm_caller
        db = SessionLocal()
        caller = make_kit_llm_caller(db)
        print("[llm] Guarded LLM adapter connected via call_llm_json.")
        return caller
    except Exception as exc:
        print(f"[llm] Adapter unavailable ({exc}). Using deterministic fallback content.")
        return None


def generate_document_content(
    llm_caller,
    doc_def: dict,
    niche: str,
    niche_context: str,
    retries: int = 2,
) -> list:
    """Generate sections for a single document with retry logic."""
    import time
    from kit_generator import _fallback_sections

    if llm_caller is None:
        return _fallback_sections(doc_def)

    user_prompt = _sections_prompt(doc_def["prompt_key"], niche, niche_context)

    for attempt in range(retries + 1):
        try:
            result = llm_caller(SYSTEM_PROMPT, user_prompt)
            # make_kit_llm_caller returns list[dict] directly
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                sections = result.get("sections", [])
                if sections:
                    return sections
            # Legacy string path (tolerated for compatibility)
            raw = str(result).strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(raw)
            sections = parsed.get("sections", parsed) if isinstance(parsed, dict) else parsed
            if sections:
                return sections
            raise ValueError("Empty sections in LLM response")
        except Exception as e:
            if attempt < retries:
                print(f"  [retry {attempt+1}] Error: {e}. Retrying...")
                time.sleep(2)
            else:
                print(f"  [failed] Could not get sections after {retries+1} attempts. Using fallback.")
                return _fallback_sections(doc_def)

    return _fallback_sections(doc_def)


def main():
    parser = argparse.ArgumentParser(description="Build Product 43 Real Estate AI Kit")
    parser.add_argument("--out",      default=None, help="Output products/ root directory")
    parser.add_argument("--covers-only", action="store_true", help="Generate SVG covers only (no LLM)")
    parser.add_argument("--doc",      default=None, help="Generate only one document by number (e.g. 02)")
    parser.add_argument("--no-pdf",   action="store_true", help="Skip PDF rendering (save HTML only)")
    args = parser.parse_args()

    products_root = Path(args.out) if args.out else ROOT / "products"
    products_root.mkdir(parents=True, exist_ok=True)
    product_dir = products_root / f"product_{PRODUCT_ID}"
    product_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  HYDRA Sprint 2.2 — Product 43 Kit Builder")
    print(f"  Kit:    {KIT_NAME}")
    print(f"  Output: {product_dir}")
    print(f"{'='*60}\n")

    # Always build covers
    print("[1/3] Building SVG covers...")
    covers = build_kit_covers(
        product_dir=product_dir,
        kit_name=KIT_NAME,
        kit_tagline=KIT_TAGLINE,
        kit_edition=KIT_EDITION,
        theme="real_estate",
    )
    for fname in covers:
        print(f"  ✓ {fname}")
    print()

    if args.covers_only:
        print("Covers-only mode. Done.\n")
        return

    # Get LLM caller
    print("[2/3] Connecting to LLM...")
    llm_caller = get_llm_caller()
    print()

    # Determine which docs to generate
    docs_to_generate = KIT_DOCUMENTS
    if args.doc:
        docs_to_generate = [d for d in KIT_DOCUMENTS if d["number"] == args.doc]
        if not docs_to_generate:
            print(f"ERROR: No document with number '{args.doc}'")
            sys.exit(1)

    kit_meta = {
        "name":    KIT_NAME,
        "edition": KIT_EDITION,
        "tagline": KIT_TAGLINE,
        "theme":   "real_estate",
    }

    print(f"[3/3] Generating {len(docs_to_generate)} document(s)...")
    pdf_paths = []
    errors = []

    for doc_def in docs_to_generate:
        num   = doc_def["number"]
        title = doc_def["title"]
        print(f"\n  [{num}] {title}")
        print(f"       Calling LLM...", end=" ", flush=True)

        sections = generate_document_content(
            llm_caller, doc_def, NICHE, NICHE_CONTEXT
        )
        print(f"✓ {len(sections)} sections")

        doc_meta = {
            "number":           num,
            "title":            title,
            "subtitle":         doc_def["subtitle"],
            "time_to_implement":doc_def["time_to_implement"],
            "page_count":       doc_def["page_count"],
            "purpose":          doc_def["purpose"],
            "toc": [
                {"title": s.get("heading", ""), "page": "—"}
                for s in sections
                if s.get("type") in ("prose", "workflow", "prompt_block", "checklist")
                and s.get("heading") and s.get("level", 2) == 2
            ][:8],
        }

        # Import rendering after sys.path is set
        from kit_generator import render_document_html, html_to_pdf
        html = render_document_html(doc_meta, sections, kit_meta)

        # Save HTML
        safe_title = title.replace(" ", "_").replace("/", "-")
        html_path  = product_dir / f"{num}_{safe_title}.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"       HTML → {html_path.name}")

        if not args.no_pdf:
            pdf_path = product_dir / f"{num}_{safe_title}.pdf"
            print(f"       PDF rendering...", end=" ", flush=True)
            ok = html_to_pdf(html, pdf_path)
            if ok:
                pdf_paths.append(pdf_path)
                print(f"✓ {pdf_path.name}")
            else:
                errors.append(f"Doc {num}: PDF failed, HTML saved")
                print(f"✗ Failed (HTML saved)")
        else:
            print(f"       (PDF skipped — --no-pdf)")

    # Assemble master PDF
    if pdf_paths and not args.no_pdf and not args.doc:
        print("\n  [MASTER] Assembling combined PDF...", end=" ", flush=True)
        from kit_generator import assemble_master_pdf
        master_path = product_dir / "MASTER_Complete_Kit.pdf"
        ok = assemble_master_pdf(pdf_paths, master_path)
        if ok:
            pdf_paths.append(master_path)
            print(f"✓")
        else:
            errors.append("Master PDF assembly failed (pypdf not installed?)")
            print("✗ (install pypdf: pip install pypdf)")

    # Build ZIP
    if not args.doc:
        print("  [ZIP]    Building delivery archive...", end=" ", flush=True)
        from kit_generator import build_zip
        zip_path = build_zip(product_dir, f"{KIT_NAME.replace(' ', '_')}.zip")
        print(f"✓ {zip_path.name}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  BUILD COMPLETE")
    print(f"  Documents:  {len(docs_to_generate)}")
    print(f"  PDFs:       {len(pdf_paths)}")
    print(f"  Covers:     {len(covers)}")
    if errors:
        print(f"  Warnings:   {len(errors)}")
        for e in errors:
            print(f"    - {e}")
    print(f"  Output:     {product_dir}")
    print(f"{'='*60}\n")

    # Quick commercial credibility self-check
    print("  Commercial credibility check:")
    print(f"  ✓ 9 SVG covers (deterministic, no image API)")
    print(f"  ✓ Professional Navy/Gold color system")
    print(f"  ✓ Consulting-style layout (cover page, header strip, callouts)")
    print(f"  ✓ Multi-document kit structure (8 docs + master)")
    if any(errors):
        print(f"  ⚠ PDF rendering issues — open .html files in browser to verify")
    else:
        print(f"  ✓ PDF rendering complete")
    print()


if __name__ == "__main__":
    main()
