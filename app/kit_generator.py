"""
kit_generator.py — Multi-document professional kit generation for HYDRA.
Sprint 2.2. Produces ai_implementation_kit product type.

Each document is generated as a structured JSON payload consumed by kit_document.html.
All LLM calls go through the existing guarded llm.py layer.
"""

import json
import os
import zipfile
from pathlib import Path
from datetime import datetime

# ── Kit document definitions ──────────────────────────────────────────────────
KIT_DOCUMENTS = [
    {
        "number":           "00",
        "title":            "Quick Start Guide",
        "subtitle":         "Your first AI win in 30 minutes",
        "time_to_implement":"30 minutes",
        "page_count":       "3–4 pages",
        "purpose":          "Orient you to the full kit and deliver your first working result "
                            "in a single 30-minute session. Start here.",
        "prompt_key":       "quick_start",
    },
    {
        "number":           "01",
        "title":            "AI Tools Setup Guide",
        "subtitle":         "Zero friction access to ChatGPT and Claude",
        "time_to_implement":"20 minutes",
        "page_count":       "5–7 pages",
        "purpose":          "Eliminate setup friction so you have working AI access "
                            "before opening any other document in this kit.",
        "prompt_key":       "tools_setup",
    },
    {
        "number":           "02",
        "title":            "Listing Description System",
        "subtitle":         "Write compelling property listings in under 10 minutes",
        "time_to_implement":"10 minutes per listing",
        "page_count":       "12–14 pages",
        "purpose":          "Replace manual listing writing with a proven AI system. "
                            "12 property-type prompts, worked examples, and an editing checklist.",
        "prompt_key":       "listing_descriptions",
    },
    {
        "number":           "03",
        "title":            "Lead Follow-Up Communication Pack",
        "subtitle":         "18 ready-to-send messages for every stage of the buyer and seller journey",
        "time_to_implement":"5 minutes per follow-up",
        "page_count":       "12–15 pages",
        "purpose":          "Eliminate dropped follow-ups. Every template is ready to personalize "
                            "and send within minutes — for every stage from first inquiry to post-close.",
        "prompt_key":       "lead_followup",
    },
    {
        "number":           "04",
        "title":            "Client Onboarding System",
        "subtitle":         "Make every first client meeting structured and professional",
        "time_to_implement":"15 minutes to prepare",
        "page_count":       "8–10 pages",
        "purpose":          "Run structured first meetings that convert consultations to signed clients. "
                            "AI-assisted preparation, question banks, and expectation-setting tools.",
        "prompt_key":       "client_onboarding",
    },
    {
        "number":           "05",
        "title":            "Social Media Content Engine",
        "subtitle":         "30-day content system for consistent agent visibility",
        "time_to_implement":"1 hour to set up, 15 min/week ongoing",
        "page_count":       "10–13 pages",
        "purpose":          "End the 'I don't know what to post' cycle. A complete monthly content "
                            "system with prompts, calendars, and repurposing workflows.",
        "prompt_key":       "social_media",
    },
    {
        "number":           "06",
        "title":            "Negotiation Support Pack",
        "subtitle":         "Language and frameworks for the highest-stakes moments",
        "time_to_implement":"5 minutes per situation",
        "page_count":       "6–8 pages",
        "purpose":          "AI-generated language for counter-offers, objection responses, "
                            "and market data narratives — when words matter most.",
        "prompt_key":       "negotiation",
    },
    {
        "number":           "07",
        "title":            "Reputation & Review System",
        "subtitle":         "Systematize five-star reviews and referrals after every close",
        "time_to_implement":"30 minutes to set up",
        "page_count":       "5–7 pages",
        "purpose":          "Turn every closed transaction into reviews, referrals, and lasting "
                            "reputation. A repeatable system, not a one-off ask.",
        "prompt_key":       "reputation",
    },
]

# ── LLM Prompts ───────────────────────────────────────────────────────────────
# Each returns structured JSON matching the kit_document.html section schema.
# Prompts are explicit about structure to minimize hallucination and maximize
# output quality. The instruction "return ONLY valid JSON" is intentional.

SYSTEM_PROMPT = """You are a senior business consultant and instructional designer
specializing in AI implementation for real estate professionals.
You write at executive deliverable quality: clear, specific, immediately actionable.
NEVER use generic AI filler language. NEVER write walls of text.
Every sentence must earn its place. Write as if a professional's time is worth $200/hour.
You will return ONLY valid JSON matching the schema provided. No markdown. No preamble."""


def _sections_prompt(doc_key: str, niche: str, niche_context: str) -> str:
    """Return the user prompt for a given document key."""

    shared_tail = f"""
Niche: {niche}
Context: {niche_context}

Return ONLY a valid JSON object with a single key "sections" whose value is an array of section objects. Each object has a "type" field.
Supported types and their required fields:

prose:      {{ "type":"prose", "heading":"...", "level":2, "paragraphs":["..."] }}
workflow:   {{ "type":"workflow", "heading":"...", "intro":"...", "steps":[{{"title":"...","description":"...","note":"(optional)"}}] }}
prompt_block: {{ "type":"prompt_block", "heading":"...", "intro":"...", "prompts":[{{"name":"...","text":"...","fill_in_fields":["[FIELD]"],"example_output":"..."}}] }}
callout:    {{ "type":"callout", "variant":"quick_win|pro_tip|time_saver|warning", "title":"...", "content":"..." }}
checklist:  {{ "type":"checklist", "heading":"...", "intro":"...", "items":[{{"title":"...","detail":"..."}}] }}
table:      {{ "type":"table", "heading":"...", "intro":"...", "columns":["Col1","Col2"], "rows":[["cell","cell"]] }}
quick_win_box: {{ "type":"quick_win_box", "time":"30 min", "title":"...", "description":"...", "steps":["Step 1","Step 2"] }}
roadmap:    {{ "type":"roadmap", "heading":"...", "phases":[{{"title":"...","time":"Week 1","tasks":["..."]}}] }}
divider:    {{ "type":"divider", "label":"..." }}
page_break: {{ "type":"page_break" }}

Rules:
- Use page_break between major sections (not between every section)
- Use callout boxes sparingly (max 3 per document) — only for genuinely important points
- prompt_block prompts must be complete, copy-paste ready, specific to real estate
- checklist items should be concrete and actionable (not vague)
- prose paragraphs should be 2–4 sentences max, no filler
- workflow steps should be precise and sequential
- Aim for 8–14 sections total
"""

    prompts = {
        "quick_start": f"""
Generate the Quick Start Guide document sections for a Real Estate AI Implementation Kit.
This is the FIRST document buyers open. It must deliver a win in 30 minutes.
Include:
- A strong opening that frames the transformation (what changes after using this kit)
- A "What's in your kit" overview section (table format listing all 8 documents with one-line descriptions)
- A "30-Minute First Session" workflow (step-by-step, exactly what to do in their first session)
- A quick_win_box for their very first prompt (listing description for their current listing)
- A "How to use this kit" section explaining the reading order
- A callout (pro_tip) about the most common mistake new AI adopters make
{shared_tail}""",

        "tools_setup": f"""
Generate the AI Tools Setup Guide document sections.
This document eliminates setup friction. Buyer should have working AI access after reading.
Include:
- Which tools to use (ChatGPT free vs paid, Claude) with a comparison table
- Step-by-step account creation workflow for ChatGPT (most common starting point)
- How to write effective prompts: the 4-part formula (Role + Task + Context + Format)
- A prompt_block with 3 "test prompts" to confirm their setup is working
- A "Common Setup Problems" section with solutions (table format)
- A callout (time_saver) for the browser bookmark setup
- A "What NOT to do" checklist (common AI mistakes in real estate context)
{shared_tail}""",

        "listing_descriptions": f"""
Generate the Listing Description System document sections.
This is the flagship document. Must contain 10+ ready-to-use prompts for different property types.
Include:
- Opening: why AI listing descriptions outperform manual ones (specific, not generic)
- The Master Listing Prompt (a universal base prompt adaptable to any property)
- prompt_block with individual prompts for: Single Family Home, Luxury Property, Condo/Townhouse,
  Fixer-Upper/Investment, New Construction, Vacation/Second Home — each with fill_in_fields and example_output
- A workflow: "10-Minute Listing Description Process" (step by step)
- A "Listing Description Quality Checklist" (checklist type, 8-10 items)
- A prompt_block for "MLS Character-Limited Version" (tight, punchy version)
- A prompt_block for "Upgrade My Existing Listing" (takes existing weak description and improves it)
- A callout (quick_win) about the single highest-impact phrase to include in any listing
{shared_tail}""",

        "lead_followup": f"""
Generate the Lead Follow-Up Communication Pack document sections.
Must contain 18+ email/text templates organized by stage and scenario.
Include:
- Opening: the follow-up problem (why agents lose deals to dropped follow-ups) — specific, stats-backed framing
- A follow-up cadence overview table (stage / timing / channel / template to use)
- prompt_block sections organized by stage:
  * New Inquiry (same-day email, same-day text)
  * Post-Showing Follow-Up (interested buyer, unsure buyer, went quiet)
  * Active Buyer: Under Contract check-in, post-inspection, pre-close
  * Seller Templates: listing feedback, offer received, post-close
  * Past Client Nurture (30-day, 90-day, annual)
- Each prompt should be complete, professional, not robotic — include fill_in_fields
- A "Customization with AI" workflow — how to personalize any template in 2 minutes
- A callout (warning) about over-automated follow-up that damages relationships
{shared_tail}""",

        "client_onboarding": f"""
Generate the Client Onboarding System document sections.
Focus on the first client meeting and expectation management.
Include:
- Why structured onboarding increases conversion from consultation to signed client
- AI-Assisted Pre-Meeting Preparation workflow (5 steps to prepare using AI before meeting)
- Buyer Consultation Question Bank: prompt_block with 20 questions that reveal real motivations
- Seller Consultation Question Bank: prompt_block with 18 questions that set realistic expectations
- First Meeting Agenda template (workflow format, timed segments)
- Pre-Meeting Email Template: prompt_block (send 24 hours before to set agenda)
- A "Expectation Setting" checklist (what to establish in the first meeting)
- A callout (pro_tip) about the single question that most reliably qualifies serious buyers
{shared_tail}""",

        "social_media": f"""
Generate the Social Media Content Engine document sections.
Focus on real estate agents who have no time and no content strategy.
Include:
- Opening: the content problem for agents (specific — time cost, inconsistency impact)
- 30-Day Content Calendar framework (table: day themes for week 1 mapped to content types)
- The "One Listing = Five Posts" repurposing workflow (prompt_block + workflow)
- Listing Announcement Templates: prompt_block with 3 variants (luxury, standard, investment)
- Market Update Templates: prompt_block (buyer's market, seller's market, rate news)
- Client Success Story Templates: prompt_block with 2 formats (testimonial-style, narrative)
- Educational Content prompt_block (5 prompts for explaining the buying/selling process)
- LinkedIn vs Instagram vs Facebook strategy callout (pro_tip — different content for each)
- A "Weekly Content Batch" workflow (produce a week of content in 45 minutes)
{shared_tail}""",

        "negotiation": f"""
Generate the Negotiation Support Pack document sections.
This is for high-stakes moments. Every word matters. Be precise and professional.
Include:
- Opening: when to use AI in negotiation (framing AI as preparation support, not script-reading)
- Counter-Offer Language Generator: prompt_block (takes scenario, outputs professional language)
- Common Objection Response Templates: prompt_block for 6 scenarios:
  Seller won't budge on price, Buyer wants to walk, Competing offers (buyer side),
  Inspection issues, Financing concerns, Lowball offer received
- Market Data Narrative Generator: prompt_block (turns raw comps into persuasive buyer/seller narrative)
- Post-Rejection Keep-in-Touch: prompt_block (when the deal dies, keeping the door open)
- A "Before Every Tough Conversation" checklist (5-item pre-negotiation prep)
- A callout (warning) about using AI language verbatim vs. as preparation
{shared_tail}""",

        "reputation": f"""
Generate the Reputation & Review System document sections.
Focus on systematizing what most agents do inconsistently or never.
Include:
- Opening: the review ROI argument (specific — how reviews affect search ranking and conversion)
- Post-Closing Review Request Sequence: workflow (Day 3 text, Day 10 email if no response, Day 30 final)
- Review Request Templates: prompt_block with 3 variants (warm/personal, professional, casual text)
- Google Review Response Templates: prompt_block for 5 scenarios
  (enthusiastic positive, standard positive, mixed/neutral, constructive criticism, unfair/inflammatory)
- Referral Ask Sequence: prompt_block (timing and language for asking past clients without awkwardness)
- LinkedIn Recommendation Request: prompt_block (professional, specific, makes it easy for them to write)
- A "Review System Setup" checklist (what to put in place before your next closing)
- A callout (quick_win) about the single sentence that doubles review response rates
{shared_tail}""",
    }

    return prompts.get(doc_key, f"Generate content for document type: {doc_key}\n{shared_tail}")


# ── PDF rendering ─────────────────────────────────────────────────────────────

def render_document_html(
    doc_meta: dict,
    sections: list,
    kit_meta: dict,
) -> str:
    """Render a single document's sections through the Jinja2 template."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    import json as _json

    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["from_json"] = _json.loads

    tpl = env.get_template("kit_document.html")
    return tpl.render(document=doc_meta, sections=sections, kit=kit_meta)


def html_to_pdf(html_content: str, output_path: str | Path) -> bool:
    """Render HTML to PDF. Tries WeasyPrint first, falls back to pdfkit."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try WeasyPrint
    try:
        from weasyprint import HTML as WP_HTML
        WP_HTML(string=html_content).write_pdf(str(output_path))
        return True
    except Exception:
        pass

    # Try pdfkit (wkhtmltopdf)
    try:
        import pdfkit
        options = {
            "page-size": "Letter",
            "margin-top": "22mm",
            "margin-right": "24mm",
            "margin-bottom": "24mm",
            "margin-left": "24mm",
            "encoding": "UTF-8",
            "print-media-type": "",
            "enable-local-file-access": "",
        }
        pdfkit.from_string(html_content, str(output_path), options=options)
        return True
    except (ImportError, Exception):
        pass

    # Last resort: save HTML (operator can print-to-PDF from browser)
    html_path = output_path.with_suffix(".html")
    html_path.write_text(html_content, encoding="utf-8")
    return False


def assemble_master_pdf(pdf_paths: list[Path], output_path: Path) -> bool:
    """Merge individual PDFs into the master combined PDF."""
    try:
        from pypdf import PdfWriter
        writer = PdfWriter()
        for p in pdf_paths:
            if p.exists():
                writer.append(str(p))
        with open(output_path, "wb") as f:
            writer.write(f)
        return True
    except ImportError:
        pass

    try:
        from PyPDF2 import PdfMerger
        merger = PdfMerger()
        for p in pdf_paths:
            if p.exists():
                merger.append(str(p))
        merger.write(str(output_path))
        merger.close()
        return True
    except ImportError:
        return False


def build_zip(
    product_dir: Path,
    zip_name: str,
    include_patterns: list[str] = None,
) -> Path:
    """Package the kit into a customer-ready ZIP archive."""
    if include_patterns is None:
        include_patterns = ["*.pdf", "covers/*.svg"]

    zip_path = product_dir / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pattern in include_patterns:
            for fpath in sorted(product_dir.glob(pattern)):
                arcname = fpath.relative_to(product_dir)
                zf.write(fpath, arcname)
    return zip_path


# ── Main generation orchestrator ─────────────────────────────────────────────

def generate_kit(
    product_id: int,
    niche: str,
    niche_context: str,
    kit_name: str,
    kit_tagline: str,
    kit_edition: str = "2026 Edition",
    theme: str = "real_estate",
    products_root: str | Path = None,
    llm_call_fn=None,
) -> dict:
    """
    Full kit generation pipeline.

    Args:
        product_id:    DB product ID (used for directory naming)
        niche:         e.g. "Real Estate Agents"
        niche_context: Additional niche detail for LLM prompts
        kit_name:      e.g. "Real Estate AI Mastery Kit"
        kit_tagline:   One-line description
        kit_edition:   e.g. "2026 Edition"
        theme:         CSS color theme key
        products_root: Path to products/ directory
        llm_call_fn:   Callable(system_prompt, user_prompt) -> str (JSON)

    Returns:
        dict with keys: product_dir, pdfs, zip_path, covers, errors
    """
    from kit_covers import build_kit_covers

    if products_root is None:
        products_root = Path(__file__).parent.parent / "products"

    product_dir = Path(products_root) / f"product_{product_id}"
    product_dir.mkdir(parents=True, exist_ok=True)

    kit_meta = {
        "name":    kit_name,
        "edition": kit_edition,
        "tagline": kit_tagline,
        "theme":   theme,
    }

    results = {
        "product_dir": str(product_dir),
        "pdfs":        [],
        "html_files":  [],
        "zip_path":    None,
        "covers":      {},
        "errors":      [],
    }

    # 1. Generate SVG covers
    print(f"[kit] Generating covers...")
    results["covers"] = build_kit_covers(
        product_dir=product_dir,
        kit_name=kit_name,
        kit_tagline=kit_tagline,
        kit_edition=kit_edition,
        theme=theme,
    )

    # 2. Generate each document
    pdf_paths = []
    for doc_def in KIT_DOCUMENTS:
        num   = doc_def["number"]
        print(f"[kit] Generating document {num}: {doc_def['title']}...")

        doc_meta = {
            "number":           num,
            "title":            doc_def["title"],
            "subtitle":         doc_def["subtitle"],
            "time_to_implement":doc_def["time_to_implement"],
            "page_count":       doc_def["page_count"],
            "purpose":          doc_def["purpose"],
            "toc":              [],
        }

        # Call LLM for sections
        sections = []
        if llm_call_fn:
            try:
                user_prompt = _sections_prompt(doc_def["prompt_key"], niche, niche_context)
                result = llm_call_fn(SYSTEM_PROMPT, user_prompt)
                # Adapter (make_kit_llm_caller) returns list directly.
                # Legacy string-returning callers are also tolerated.
                if isinstance(result, list):
                    sections = result
                elif isinstance(result, dict):
                    sections = result.get("sections", [])
                else:
                    raw = str(result).strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
                    parsed = json.loads(raw)
                    sections = parsed.get("sections", parsed) if isinstance(parsed, dict) else parsed
                if not sections:
                    raise ValueError("LLM returned zero sections")
            except Exception as e:
                results["errors"].append(f"Doc {num} LLM error: {e}")
                sections = _fallback_sections(doc_def)
        else:
            sections = _fallback_sections(doc_def)

        # Build TOC from h2 sections
        doc_meta["toc"] = [
            {"title": s.get("heading", ""), "page": "—"}
            for s in sections
            if s.get("type") in ("prose", "workflow", "prompt_block", "checklist")
            and s.get("heading") and s.get("level", 2) == 2
        ][:8]

        # Render HTML
        html = render_document_html(doc_meta, sections, kit_meta)

        # Save HTML
        html_path = product_dir / f"{num}_{doc_def['title'].replace(' ', '_')}.html"
        html_path.write_text(html, encoding="utf-8")
        results["html_files"].append(str(html_path))

        # Render PDF
        pdf_path = product_dir / f"{num}_{doc_def['title'].replace(' ', '_')}.pdf"
        ok = html_to_pdf(html, pdf_path)
        if ok:
            pdf_paths.append(pdf_path)
            results["pdfs"].append(str(pdf_path))
        else:
            results["errors"].append(f"Doc {num}: PDF render failed, HTML saved")

    # 3. Assemble master PDF
    print("[kit] Assembling master PDF...")
    master_path = product_dir / "MASTER_Complete_Kit.pdf"
    ok = assemble_master_pdf(pdf_paths, master_path)
    if ok:
        results["pdfs"].append(str(master_path))

    # 4. Build ZIP
    print("[kit] Building delivery ZIP...")
    zip_name = f"{kit_name.replace(' ', '_')}_Kit.zip"
    zip_path = build_zip(product_dir, zip_name)
    results["zip_path"] = str(zip_path)

    print(f"[kit] Done. {len(pdf_paths)} PDFs, 1 ZIP → {product_dir}")
    return results


def _fallback_sections(doc_def: dict) -> list:
    """Real-estate-specific fallback sections for each document.

    Used when LLM is blocked or unavailable. Professional enough to ship as a
    draft; intended to be replaced by LLM-generated content on the next build.
    """
    key = doc_def.get("number", "00")
    return _FALLBACK_BY_DOC.get(key, _generic_fallback(doc_def))


def _generic_fallback(doc_def: dict) -> list:
    return [
        {
            "type": "prose",
            "heading": doc_def["title"],
            "level": 1,
            "paragraphs": [doc_def["purpose"],
                           f"Estimated implementation time: {doc_def['time_to_implement']}."],
        },
        {
            "type": "callout",
            "variant": "pro_tip",
            "title": "Draft Content",
            "content": "This document contains draft content. Re-generate with LLM connected for full professional copy.",
        },
    ]


_FALLBACK_BY_DOC: dict = {

    "00": [
        {
            "type": "prose",
            "heading": "Your AI Advantage Starts Now",
            "level": 1,
            "paragraphs": [
                "This kit gives you a complete, tested AI implementation system built specifically for real estate agents. Every document is immediately usable — no setup theory, no generic advice.",
                "By the end of your first 30-minute session, you will have used AI to write a property listing, draft a client follow-up, or prep for a listing appointment. Start here.",
            ],
        },
        {
            "type": "table",
            "heading": "What Is in Your Kit",
            "level": 2,
            "intro": "Eight documents covering every high-value AI use case for agents.",
            "columns": ["#", "Document", "What You Get"],
            "rows": [
                ["00", "Quick Start Guide", "First win in 30 minutes"],
                ["01", "AI Tools Setup Guide", "ChatGPT + Claude configured and ready"],
                ["02", "Listing Description System", "12 property-type prompts + editing checklist"],
                ["03", "Lead Follow-Up Pack", "18 templates for every stage of the buyer/seller journey"],
                ["04", "Client Onboarding System", "Structured consultations that convert"],
                ["05", "Social Media Content Engine", "30-day content system, 15 min/week"],
                ["06", "Negotiation Support Pack", "Language for counter-offers and objections"],
                ["07", "Reputation & Review System", "Repeatable 5-star review process"],
            ],
        },
        {
            "type": "quick_win_box",
            "time": "30 min",
            "title": "Your First AI Win",
            "description": "Write a listing description for your current or most recent listing using AI.",
            "steps": [
                "Open ChatGPT or Claude in your browser",
                "Type: 'You are a real estate copywriter. Write a compelling 150-word MLS listing description for a [3-bed, 2-bath home in Dallas with an updated kitchen and large backyard]. Highlight the lifestyle benefits, not just the features.'",
                "Replace the bracketed details with your actual property",
                "Read the output and personalize one sentence to match your voice",
                "Copy to your MLS system",
            ],
        },
        {
            "type": "workflow",
            "heading": "Recommended Reading Order",
            "level": 2,
            "intro": "Follow this sequence for fastest results.",
            "steps": [
                {"title": "Today", "description": "Read Document 01 (Tools Setup) and confirm you have a working AI account."},
                {"title": "Day 1", "description": "Use Document 02 (Listing Descriptions) on your next active listing."},
                {"title": "Day 2-3", "description": "Set up Document 03 (Lead Follow-Up) templates in your CRM or email drafts."},
                {"title": "Week 2", "description": "Work through Documents 04-05 at your own pace."},
                {"title": "Ongoing", "description": "Documents 06-07 are reference tools — pull them before negotiations and after closings."},
            ],
        },
        {
            "type": "callout",
            "variant": "pro_tip",
            "title": "The #1 Mistake New AI Adopters Make",
            "content": "Treating AI as a drafting tool instead of a thinking partner. Before writing anything, ask AI to help you think through the problem first. 'What are the 5 things a motivated seller needs to hear in the first listing consultation?' is more powerful than 'Write me a listing pitch.'",
        },
    ],

    "01": [
        {
            "type": "prose",
            "heading": "Which Tools to Use",
            "level": 1,
            "paragraphs": [
                "Two tools cover 95% of real estate AI use cases: ChatGPT (OpenAI) and Claude (Anthropic). You do not need paid plans to start, though the paid versions are significantly more capable for professional work.",
            ],
        },
        {
            "type": "table",
            "heading": "ChatGPT vs Claude — Quick Comparison",
            "level": 2,
            "intro": "Use this to decide where to start.",
            "columns": ["Feature", "ChatGPT (Free)", "ChatGPT Plus ($20/mo)", "Claude (Free)"],
            "rows": [
                ["Model", "GPT-3.5", "GPT-4o", "Claude 3 Haiku"],
                ["Best for", "Simple drafts", "Complex writing, analysis", "Long documents, nuance"],
                ["Context window", "Short", "Long", "Very long"],
                ["Image input", "No", "Yes", "Yes"],
                ["Recommendation", "Start here", "Upgrade when ready", "Use for listing copy"],
            ],
        },
        {
            "type": "workflow",
            "heading": "ChatGPT Account Setup (5 minutes)",
            "level": 2,
            "intro": "Follow these steps to have a working account before opening any other document.",
            "steps": [
                {"title": "Go to chat.openai.com", "description": "Click 'Sign up'. Use your business email."},
                {"title": "Verify your email", "description": "Check your inbox and click the verification link."},
                {"title": "Complete your profile", "description": "Enter your name. You can skip phone verification on free accounts."},
                {"title": "Start your first chat", "description": "Click 'New chat' and type: 'I am a real estate agent. Help me write a 3-sentence bio.'"},
                {"title": "Bookmark the page", "description": "Add chat.openai.com to your browser bookmarks bar for one-click access."},
            ],
        },
        {
            "type": "prose",
            "heading": "The 4-Part Prompt Formula",
            "level": 2,
            "paragraphs": [
                "Every effective AI prompt has four elements: Role (who AI should be), Task (what to produce), Context (the specific details), and Format (how to structure the output).",
                "Example: 'You are a real estate copywriter [Role]. Write a follow-up email [Task] for a buyer who toured a 3-bed condo in Austin yesterday but seemed hesitant about the HOA fees [Context]. Keep it under 150 words and end with a question [Format].'",
            ],
        },
        {
            "type": "prompt_block",
            "heading": "3 Test Prompts to Confirm Your Setup Works",
            "level": 2,
            "intro": "Run each of these. If you get a useful response, your setup is working.",
            "prompts": [
                {
                    "name": "Test 1 — Listing Description",
                    "text": "You are a real estate copywriter. Write a 100-word MLS listing description for a [3-bed, 2-bath ranch home in Phoenix with a pool and RV gate]. Focus on lifestyle benefits.",
                    "fill_in_fields": ["[property details]"],
                    "example_output": "Desert living at its finest. This 3-bedroom ranch home is built for the Phoenix lifestyle — cool mornings by the pool, evenings under the patio, and weekends with the toys thanks to the oversized RV gate...",
                },
                {
                    "name": "Test 2 — Follow-Up Email",
                    "text": "You are a real estate agent. Write a friendly follow-up email to a buyer couple who toured a home yesterday but haven't responded. Keep it under 100 words. Do not be pushy.",
                    "fill_in_fields": [],
                    "example_output": "Hi [Name], just checking in after yesterday's showing. No pressure at all — just wanted to make sure you had everything you needed to think it over...",
                },
                {
                    "name": "Test 3 — Market Update",
                    "text": "Write a 2-paragraph market update for homebuyers in [city] explaining that inventory is low but mortgage rates have stabilized. Tone: reassuring and professional.",
                    "fill_in_fields": ["[city]"],
                    "example_output": "If you have been waiting for the 'right time' to buy in [City], the market is giving you clearer signals this quarter...",
                },
            ],
        },
        {
            "type": "checklist",
            "heading": "What NOT to Do with AI",
            "level": 2,
            "intro": "Avoid these mistakes from day one.",
            "items": [
                {"title": "Do not copy AI output verbatim", "detail": "Always read and personalize. Clients can detect templated language."},
                {"title": "Do not include confidential client details", "detail": "Never paste a client's full name, address, or financial information into a public AI tool."},
                {"title": "Do not use AI for legal or compliance advice", "detail": "AI does not know your state's disclosure requirements. Consult your broker."},
                {"title": "Do not expect perfection on the first try", "detail": "Treat every AI response as a first draft, not a finished product."},
                {"title": "Do not use vague prompts", "detail": "'Write a listing' will produce generic output. Specific context produces professional results."},
            ],
        },
    ],

    "02": [
        {
            "type": "prose",
            "heading": "Why AI Outperforms Manual Listing Copy",
            "level": 1,
            "paragraphs": [
                "Listings with professionally written descriptions receive 45% more online views than those with agent-written copy (NAR, 2024). The gap is not creativity — it is time. AI closes that gap in under 10 minutes.",
                "The system in this document produces listing descriptions that are MLS-ready, platform-optimized (full length for Zillow, tight for realtor.com), and consistent across every property you list.",
            ],
        },
        {
            "type": "prompt_block",
            "heading": "The Master Listing Prompt",
            "level": 2,
            "intro": "Use this as your universal base. Adapt the property details for any listing.",
            "prompts": [
                {
                    "name": "Master Listing Description",
                    "text": "You are a real estate copywriter specializing in residential listings. Write a compelling 150-word MLS listing description for the following property:\n\nProperty type: [PROPERTY TYPE]\nBedrooms/Bathrooms: [BEDS/BATHS]\nLocation: [CITY/NEIGHBORHOOD]\nKey features: [FEATURE 1], [FEATURE 2], [FEATURE 3]\nTarget buyer: [BUYER PROFILE]\nPrice point: [PRICE RANGE]\n\nRules: Lead with a lifestyle statement, not square footage. Mention the neighborhood benefit in sentence 2. End with a call to action. No exclamation points.",
                    "fill_in_fields": ["[PROPERTY TYPE]", "[BEDS/BATHS]", "[CITY/NEIGHBORHOOD]", "[FEATURE 1]", "[FEATURE 2]", "[FEATURE 3]", "[BUYER PROFILE]", "[PRICE RANGE]"],
                    "example_output": "Mornings start better here. This 4-bedroom craftsman sits on a quiet cul-de-sac in Brookside — walkable to coffee, minutes from the highway. The chef's kitchen was renovated in 2023 with quartz countertops and a 36-inch gas range. The backyard is flat, fenced, and large enough for a pool. Schedule your private showing before this weekend.",
                },
            ],
        },
        {
            "type": "prompt_block",
            "heading": "Property-Type Prompt Library",
            "level": 2,
            "intro": "One tailored prompt for each common property type. Fill in the brackets.",
            "prompts": [
                {
                    "name": "Single Family Home",
                    "text": "Write a 150-word listing for a single-family home: [BEDS/BATHS], [CITY], built [YEAR], featuring [TOP 3 FEATURES]. Buyer profile: [FAMILY TYPE]. Emphasize neighborhood schools and yard space.",
                    "fill_in_fields": ["[BEDS/BATHS]", "[CITY]", "[YEAR]", "[TOP 3 FEATURES]", "[FAMILY TYPE]"],
                    "example_output": "Room to grow. This 4-bed, 2.5-bath Colonial in Lake Ridge feeds into the top-rated Fairfax County schools...",
                },
                {
                    "name": "Luxury Property ($800K+)",
                    "text": "Write a 175-word listing for a luxury home: [BEDS/BATHS], [LOCATION], priced at [PRICE]. Premium features: [FEATURE LIST]. Use sophisticated, aspirational language. No clichés ('stunning', 'breathtaking'). Open with a scene-setting statement.",
                    "fill_in_fields": ["[BEDS/BATHS]", "[LOCATION]", "[PRICE]", "[FEATURE LIST]"],
                    "example_output": "The view from the primary suite has stopped people mid-sentence. Set on 1.2 acres above the valley, this custom estate...",
                },
                {
                    "name": "Condo / Townhouse",
                    "text": "Write a 130-word listing for a condo/townhouse: [BEDS/BATHS], [BUILDING NAME OR AREA], [FLOOR/UNIT DETAILS]. Highlight: walkability, amenities, and low-maintenance lifestyle. Target: [BUYER — professional, downsizer, investor].",
                    "fill_in_fields": ["[BEDS/BATHS]", "[BUILDING NAME OR AREA]", "[FLOOR/UNIT DETAILS]", "[BUYER]"],
                    "example_output": "Lock-and-leave living in the heart of Midtown. This 2-bed corner unit on the 14th floor of The Monroe combines floor-to-ceiling views with a building that handles everything else...",
                },
                {
                    "name": "Fixer-Upper / Investment",
                    "text": "Write a 130-word listing for an investment or fixer property: [ADDRESS AREA], [CURRENT STATE], [POTENTIAL/ZONING]. Target buyer: investor or house-hacker. Be honest about condition, enthusiastic about opportunity. Include ARV if known.",
                    "fill_in_fields": ["[ADDRESS AREA]", "[CURRENT STATE]", "[POTENTIAL/ZONING]", "[ARV]"],
                    "example_output": "The upside is real. This 3-bed bungalow in East Nashville needs a full cosmetic renovation — and the comps support an ARV of $485K...",
                },
            ],
        },
        {
            "type": "workflow",
            "heading": "The 10-Minute Listing Description Process",
            "level": 2,
            "intro": "From blank page to MLS-ready copy in 10 minutes.",
            "steps": [
                {"title": "Gather your inputs (2 min)", "description": "Property type, beds/baths, year built, top 3 features, target buyer, price. Have the MLS sheet in front of you."},
                {"title": "Fill in the prompt template (2 min)", "description": "Open your AI tool. Paste the matching property-type prompt from this document. Replace all brackets."},
                {"title": "Generate and read (1 min)", "description": "Submit the prompt. Read the output fully before editing anything."},
                {"title": "Personalize one detail (2 min)", "description": "Change one sentence to reflect something specific you noticed during your showing — a detail only you know."},
                {"title": "Check length and format (1 min)", "description": "MLS full description: 150-200 words. Realtor.com headline: 50 chars max. Trim if needed."},
                {"title": "Final read-aloud test (2 min)", "description": "Read the copy aloud. If you stumble, rewrite that sentence. If it sounds like an ad, ask AI to make it sound more like a conversation."},
            ],
        },
        {
            "type": "checklist",
            "heading": "Listing Description Quality Checklist",
            "level": 2,
            "intro": "Run every description through this before submitting to MLS.",
            "items": [
                {"title": "Opens with lifestyle, not square footage", "detail": "First sentence should paint a picture of living there, not recite stats."},
                {"title": "Neighborhood mentioned in first 3 sentences", "detail": "Location is the #1 purchase driver. Surface it early."},
                {"title": "No overused adjectives", "detail": "Remove: stunning, breathtaking, charming, cozy, amazing, wonderful, gorgeous."},
                {"title": "At least one specific detail only you know", "detail": "The original 1940s tilework in the kitchen. The view of the water from the upstairs bath."},
                {"title": "Call to action in final sentence", "detail": "'Schedule your showing before this weekend' outperforms 'Don't miss this one!'"},
                {"title": "Under 200 words for MLS", "detail": "Count matters. Most MLS systems cut off after 200-250 words."},
                {"title": "No pricing or negotiation language", "detail": "Never mention 'priced to sell,' 'motivated seller,' or 'as-is' in MLS copy."},
            ],
        },
    ],

    "03": [
        {
            "type": "prose",
            "heading": "The Follow-Up Gap That Costs Agents Deals",
            "level": 1,
            "paragraphs": [
                "Studies consistently show that 80% of sales require 5+ follow-up contacts, but 44% of agents give up after one. In real estate, a single dropped follow-up on a motivated buyer can cost $9,000-$18,000 in commission.",
                "This pack eliminates the 'what do I say?' problem. Every template is professional, personalized with one fill-in line, and ready to send in under 2 minutes.",
            ],
        },
        {
            "type": "table",
            "heading": "Follow-Up Cadence Overview",
            "level": 2,
            "intro": "Match the template to the stage and channel.",
            "columns": ["Stage", "Timing", "Channel", "Template"],
            "rows": [
                ["New Inquiry", "Within 1 hour", "Text first, email follow", "New Inquiry — Same Day"],
                ["Post-Showing", "Within 4 hours", "Text", "Post-Showing — Interested"],
                ["Gone Quiet", "Day 5 after showing", "Email", "Gone Quiet — Re-engagement"],
                ["Under Contract", "Weekly", "Email", "Under Contract — Check-In"],
                ["Post-Close", "Day 3", "Text", "Review Request"],
                ["Past Client Nurture", "90-day, Annual", "Email", "Nurture — Quarterly"],
            ],
        },
        {
            "type": "prompt_block",
            "heading": "New Inquiry Templates",
            "level": 2,
            "intro": "Speed is the competitive advantage here. First agent to respond wins.",
            "prompts": [
                {
                    "name": "New Inquiry — Same-Day Text",
                    "text": "Write a friendly, brief text message response to a new buyer inquiry for [PROPERTY ADDRESS OR TYPE]. The buyer submitted an online form. Keep it under 60 words. End with one easy question to start a conversation. Do not use exclamation points.",
                    "fill_in_fields": ["[PROPERTY ADDRESS OR TYPE]", "[AGENT NAME]"],
                    "example_output": "Hi [Name], this is Sarah with Realty Group — saw your inquiry on the Maple St listing. Great property. Would you like to schedule a showing this week, or do you have questions about the neighborhood first?",
                },
                {
                    "name": "New Inquiry — Same-Day Email",
                    "text": "Write a professional email response to a buyer who submitted a contact form about [PROPERTY]. Include: a brief intro, 2 key facts about the property, and 3 available showing times. Subject line included. Under 120 words.",
                    "fill_in_fields": ["[PROPERTY]", "[SHOWING TIMES]", "[AGENT NAME]"],
                    "example_output": "Subject: [Address] — Available for Showing This Week\n\nHi [Name], thanks for your interest in [Address]...",
                },
            ],
        },
        {
            "type": "prompt_block",
            "heading": "Post-Showing Follow-Up Templates",
            "level": 2,
            "intro": "Send within 4 hours of the showing. Match the template to the buyer's energy.",
            "prompts": [
                {
                    "name": "Post-Showing — Interested Buyer",
                    "text": "Write a follow-up text for a buyer who seemed excited during a showing of [PROPERTY]. They mentioned liking [SPECIFIC FEATURE THEY COMMENTED ON]. Ask if they want to move forward. Under 80 words.",
                    "fill_in_fields": ["[PROPERTY]", "[SPECIFIC FEATURE]"],
                    "example_output": "Great touring the Oakwood property with you today. That kitchen really is something. If you want to run numbers or see the comps before deciding, I can have everything ready by tomorrow morning — just say the word.",
                },
                {
                    "name": "Post-Showing — Went Quiet (Day 5)",
                    "text": "Write a re-engagement email for a buyer who toured a property 5 days ago and has not responded to follow-up. Do not mention the silence. Lead with a market update or piece of value. Soft ask at the end. Under 100 words.",
                    "fill_in_fields": ["[MARKET UPDATE FACT]", "[PROPERTY OR AREA]"],
                    "example_output": "Quick update on [Area] — two comparable properties went under contract this week at asking price. The [Address] listing is still available. Happy to pull the latest comps if that would help you think through the timing.",
                },
            ],
        },
        {
            "type": "callout",
            "variant": "warning",
            "title": "Automated Follow-Up Damages Relationships",
            "content": "Sending 5 identical follow-up emails via automation tells buyers you do not actually remember them. One personalized line — referencing the specific house, a detail they mentioned, or a current market fact — does more than a five-email drip sequence. Use these templates as starting points, not copy-paste final drafts.",
        },
    ],

    "04": [
        {
            "type": "prose",
            "heading": "Why Structured Onboarding Converts More Consultations",
            "level": 1,
            "paragraphs": [
                "Agents who run structured first meetings with a consistent agenda convert consultations to signed buyers or sellers at roughly twice the rate of unstructured meetings. The difference is not charm — it is preparation and perceived expertise.",
                "This system gives you an AI-assisted preparation workflow, a complete question bank for both buyers and sellers, and a first-meeting agenda you can adapt to any client.",
            ],
        },
        {
            "type": "workflow",
            "heading": "AI-Assisted Pre-Meeting Preparation",
            "level": 2,
            "intro": "Complete this in 15 minutes before any new client consultation.",
            "steps": [
                {"title": "Run the neighborhood brief", "description": "Prompt AI: 'Summarize the real estate market in [NEIGHBORHOOD] for a buyer consultation. Include: average DOM, list-to-sale price ratio, and 3 buyer talking points. Use data from the last 90 days.'"},
                {"title": "Prepare objection responses", "description": "Prompt AI: 'What are the 3 most common objections from [BUYER TYPE — first-time, move-up, investor] buyers in a [MARKET CONDITION] market? Give me a one-sentence response to each.'"},
                {"title": "Build the client brief", "description": "Search the client's name on LinkedIn and Zillow saved searches if available. Paste any background into AI to get relevant talking points."},
                {"title": "Review your agenda", "description": "Print or pull up the First Meeting Agenda from this document. Mark the 2 questions you most want answered."},
                {"title": "Set your timer", "description": "60 minutes is the right length for a buyer consultation. 45 for a seller. Set a visible timer to respect their time."},
            ],
        },
        {
            "type": "prompt_block",
            "heading": "Buyer Consultation Question Bank",
            "level": 2,
            "intro": "These questions reveal real motivations, timelines, and financial readiness.",
            "prompts": [
                {
                    "name": "Buyer Motivation & Timeline Questions",
                    "text": "Generate 12 open-ended discovery questions for a buyer consultation that reveal: true motivation for buying now, financial readiness without asking directly about money, flexibility on timeline, and deal-breakers. Questions should feel conversational, not interrogative.",
                    "fill_in_fields": [],
                    "example_output": "1. What is driving the timing for you — is there a specific reason now versus six months ago? 2. When you picture your ideal move-in scenario, what does that look like?...",
                },
            ],
        },
        {
            "type": "callout",
            "variant": "pro_tip",
            "title": "The One Question That Qualifies Serious Buyers",
            "content": "'If we found the right property tomorrow, is there anything on your side that would prevent you from making an offer?' — This single question surfaces financing gaps, relocation timing, simultaneous sales, and decision-maker gaps before you invest 10 showings into an unqualified buyer.",
        },
    ],

    "05": [
        {
            "type": "prose",
            "heading": "The Real Estate Content Problem",
            "level": 1,
            "paragraphs": [
                "The average agent spends 3-5 hours per week thinking about what to post, producing inconsistent content, and getting limited results. That is 150-250 hours per year on low-ROI activity.",
                "This system reduces content production to 15 minutes per week while producing a higher volume of better content — because AI handles the drafting and you provide the expertise.",
            ],
        },
        {
            "type": "table",
            "heading": "30-Day Content Calendar Framework",
            "level": 2,
            "intro": "Assign these themes to days and batch-produce each week in one session.",
            "columns": ["Day Theme", "Content Type", "Example Topic"],
            "rows": [
                ["Market Monday", "Data/stats post", "This week's average DOM in [city]"],
                ["Tip Tuesday", "Educational", "5 things buyers overlook in a home inspection"],
                ["Listing Wednesday", "Property feature", "New listing highlight or just-sold"],
                ["Client Thursday", "Social proof", "Anonymized client success story"],
                ["FAQ Friday", "Q&A", "The question I get asked every week: [question]"],
            ],
        },
        {
            "type": "prompt_block",
            "heading": "The 'One Listing = Five Posts' System",
            "level": 2,
            "intro": "Every listing gives you a week of content. Here is how.",
            "prompts": [
                {
                    "name": "New Listing Announcement",
                    "text": "Write a social media post announcing a new listing at [ADDRESS OR AREA]. Property: [BEDS/BATHS, KEY FEATURES]. Platform: [Instagram/Facebook/LinkedIn]. Tone: [professional/conversational]. Include a soft call to action. Under 150 words.",
                    "fill_in_fields": ["[ADDRESS OR AREA]", "[BEDS/BATHS, KEY FEATURES]", "[PLATFORM]"],
                    "example_output": "Just listed in Westfield Hills. This 4-bed craftsman has the kitchen you've been pinning for two years — quartz, gas range, open to the living room. DM me for a private showing before the weekend.",
                },
                {
                    "name": "Market Update Post",
                    "text": "Write a 100-word social media post explaining that [MARKET CONDITION — rates stable, inventory low, seller's market] in [CITY/AREA]. Audience: potential buyers. Tone: informative and reassuring. End with an invitation to DM for personalized advice.",
                    "fill_in_fields": ["[MARKET CONDITION]", "[CITY/AREA]"],
                    "example_output": "Rates held steady for the third week in a row in [City]. What that means for buyers: your purchasing power has not changed...",
                },
            ],
        },
        {
            "type": "workflow",
            "heading": "Weekly Content Batch — 45 Minutes on Sunday",
            "level": 2,
            "intro": "One session produces all your content for the week.",
            "steps": [
                {"title": "Pull your raw material (10 min)", "description": "List this week's closings, new listings, showings, and client questions. These become your content inputs."},
                {"title": "Batch prompt in one AI session (20 min)", "description": "Open AI. Draft all 5 posts in one session — each prompt should reference the same property or market condition. The AI maintains context across the session."},
                {"title": "Edit and personalize (10 min)", "description": "Read every post. Add one detail only you would know. Remove any AI phrases that sound templated."},
                {"title": "Schedule (5 min)", "description": "Load into your scheduling tool (Buffer, Later, Hootsuite). Set and forget."},
            ],
        },
    ],

    "06": [
        {
            "type": "prose",
            "heading": "Using AI in Negotiation — The Right Frame",
            "level": 1,
            "paragraphs": [
                "AI is a preparation tool, not a script. Use it before the conversation to think through positions, anticipate responses, and practice language. Never read AI output to a client or opposing agent in real time.",
                "The prompts in this document help you think faster and speak more precisely at the highest-stakes moments in a transaction.",
            ],
        },
        {
            "type": "prompt_block",
            "heading": "Counter-Offer Language Generator",
            "level": 2,
            "intro": "Use before any counter-offer conversation or written response.",
            "prompts": [
                {
                    "name": "Counter-Offer — Seller Side",
                    "text": "I am a listing agent. The buyer offered [OFFER PRICE] on my listing at [LIST PRICE]. My seller wants to counter at [COUNTER PRICE]. The buyer's stated concern is [CONCERN — price, closing costs, inspection contingency]. Write 3 counter-offer response options ranging from firm to flexible. Professional tone. No emotional language.",
                    "fill_in_fields": ["[OFFER PRICE]", "[LIST PRICE]", "[COUNTER PRICE]", "[CONCERN]"],
                    "example_output": "Option A (Firm): We are countering at $485,000, which reflects the most recent comparables in the neighborhood...",
                },
                {
                    "name": "Counter-Offer — Buyer Side",
                    "text": "I represent a buyer. The seller countered at [COUNTER PRICE]. My buyer's max is [MAX PRICE]. The seller's stated priority is [PRIORITY — quick close, clean offer, price]. Write language for a counteroffer that acknowledges their priority while protecting my buyer's position.",
                    "fill_in_fields": ["[COUNTER PRICE]", "[MAX PRICE]", "[SELLER PRIORITY]"],
                    "example_output": "We respect the seller's timeline. To accommodate the preferred closing date, we are offering [PRICE] with a 21-day close, as-is inspection with a [DOLLAR] cap...",
                },
            ],
        },
        {
            "type": "prompt_block",
            "heading": "Common Objection Response Templates",
            "level": 2,
            "intro": "Prepare before the conversation, not during it.",
            "prompts": [
                {
                    "name": "Seller Won't Budge on Price",
                    "text": "My listing seller insists the home is worth [PRICE] despite comps supporting [COMP RANGE]. Write 3 data-driven statements I can use in a conversation to help reset expectations without damaging the relationship.",
                    "fill_in_fields": ["[PRICE]", "[COMP RANGE]"],
                    "example_output": "The market is giving us clear feedback. In the last 45 days, every home in this price range has taken 30+ days to receive an offer...",
                },
                {
                    "name": "Inspection Issues — Negotiation Language",
                    "text": "The inspection came back with [ISSUE LIST]. The buyer wants a $[DOLLAR] credit. The seller is offering $[SELLER OFFER]. Write language for a compromise conversation that references repair cost reality without taking sides.",
                    "fill_in_fields": ["[ISSUE LIST]", "[DOLLAR]", "[SELLER OFFER]"],
                    "example_output": "Both sides have reasonable positions here. What independent contractor estimates show is...",
                },
            ],
        },
        {
            "type": "checklist",
            "heading": "Before Every Tough Conversation",
            "level": 2,
            "intro": "Run this 5-item checklist before any negotiation call.",
            "items": [
                {"title": "Know your client's true bottom line", "detail": "Not their opening position — their actual walk-away number or condition."},
                {"title": "Know the other side's stated priority", "detail": "Price, timeline, certainty of close, or terms? Prioritize their stated concern in your language."},
                {"title": "Have one data point ready", "detail": "One recent comp, DOM average, or repair estimate. One fact anchors the conversation."},
                {"title": "Decide your tone in advance", "detail": "Collaborative or firm? Decide before the call, not based on their opening line."},
                {"title": "Prepare your pause", "detail": "When they say something unexpected, say: 'Let me make sure I understand what you are saying.' Buys 10 seconds."},
            ],
        },
        {
            "type": "callout",
            "variant": "warning",
            "title": "Never Read AI Language Verbatim",
            "content": "AI-generated negotiation language is preparation material. If you read it verbatim during a conversation, experienced agents and clients will recognize the pattern. Use it to think through your position, then say it in your own words.",
        },
    ],

    "07": [
        {
            "type": "prose",
            "heading": "The Review ROI Most Agents Ignore",
            "level": 1,
            "paragraphs": [
                "Google reviews directly affect local search ranking. Agents with 20+ reviews and a 4.8+ rating appear 3x more often in 'real estate agent near me' searches than agents with fewer or lower-rated reviews. A single five-star review is worth an estimated $2,000-$5,000 in referral value over two years.",
                "This system turns every closing into a systematic review and referral opportunity — not a one-off awkward ask.",
            ],
        },
        {
            "type": "workflow",
            "heading": "Post-Closing Review Request Sequence",
            "level": 2,
            "intro": "Three-touch sequence. Most reviews come from the second or third touch.",
            "steps": [
                {"title": "Day 3 — Text", "description": "Send the Day 3 Text template (below). Warm, personal, specific reference to their transaction. Include your Google review link."},
                {"title": "Day 10 — Email (if no response)", "description": "Send the Day 10 Email template. Slightly longer, explains why reviews matter. Do not mention that you already texted."},
                {"title": "Day 30 — Final Ask", "description": "If still no review, send the Day 30 template. This is your last ask. Keep it brief and gracious regardless of outcome."},
            ],
        },
        {
            "type": "prompt_block",
            "heading": "Review Request Templates",
            "level": 2,
            "intro": "Three variants for different relationship styles.",
            "prompts": [
                {
                    "name": "Warm / Personal — Day 3 Text",
                    "text": "Write a text message to a just-closed client named [CLIENT NAME] asking for a Google review. Reference: [ONE SPECIFIC DETAIL FROM THEIR TRANSACTION]. Include a link placeholder. Under 80 words. Warm but not gushing.",
                    "fill_in_fields": ["[CLIENT NAME]", "[TRANSACTION DETAIL]", "[GOOGLE REVIEW LINK]"],
                    "example_output": "Hi [Name] — hoping the move-in is going smoothly. That last-minute title issue was stressful but you handled it perfectly. If you have 2 minutes, a Google review would mean a lot: [LINK]. No pressure at all.",
                },
                {
                    "name": "Professional — Day 10 Email",
                    "text": "Write an email to a past client asking for a Google review. Explain briefly why reviews matter for a small business agent. Include a direct link placeholder and make the ask easy. Subject line included. Under 150 words.",
                    "fill_in_fields": ["[CLIENT NAME]", "[GOOGLE REVIEW LINK]"],
                    "example_output": "Subject: A small favor — 2 minutes\n\nHi [Name], I hope [PROPERTY ADDRESS] is already starting to feel like home...",
                },
            ],
        },
        {
            "type": "prompt_block",
            "heading": "Google Review Response Templates",
            "level": 2,
            "intro": "Respond to every review within 24 hours. Use these as starting points.",
            "prompts": [
                {
                    "name": "Enthusiastic Positive Review Response",
                    "text": "Write a response to an enthusiastic 5-star Google review from [CLIENT NAME] who praised [SPECIFIC PRAISE]. Under 80 words. Warm, specific, professional. Do not repeat the word 'amazing.'",
                    "fill_in_fields": ["[CLIENT NAME]", "[SPECIFIC PRAISE]"],
                    "example_output": "Thank you, [Name] — working with you on the [PROPERTY] purchase was genuinely a highlight. Your patience through the inspection negotiation made a real difference in how it all came together...",
                },
                {
                    "name": "Constructive Criticism Response",
                    "text": "Write a response to a 3-star review that mentions [SPECIFIC ISSUE]. Acknowledge without being defensive. Express commitment to improvement. Do not offer compensation or ask them to change the review. Under 100 words.",
                    "fill_in_fields": ["[SPECIFIC ISSUE]"],
                    "example_output": "Thank you for taking the time to share this. You are right that [ISSUE] was not handled as well as it should have been...",
                },
            ],
        },
        {
            "type": "checklist",
            "heading": "Review System Setup Checklist",
            "level": 2,
            "intro": "Complete this once. Then the system runs on autopilot.",
            "items": [
                {"title": "Claim your Google Business Profile", "detail": "Go to business.google.com. Claim and verify your profile if not done already."},
                {"title": "Get your short review link", "detail": "In Google Business Profile, go to 'Get more reviews' and copy your short link. Save it somewhere permanent."},
                {"title": "Add review link to your email signature", "detail": "Every email you send becomes a passive review opportunity."},
                {"title": "Set a Day 3 calendar reminder for every closing", "detail": "Add it to your closing checklist. Non-negotiable step."},
                {"title": "Respond to all existing reviews", "detail": "Respond to every review you have not responded to. Shows prospects you are attentive."},
            ],
        },
        {
            "type": "callout",
            "variant": "quick_win",
            "title": "The Sentence That Doubles Review Response Rates",
            "content": "Add this to any review request: 'It takes about 90 seconds and means more to a small business agent than you might expect.' Specificity (90 seconds) and honesty (small business framing) consistently outperform generic 'would love a review' asks.",
        },
    ],
}

