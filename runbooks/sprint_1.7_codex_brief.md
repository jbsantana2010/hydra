# Sprint 1.7 Codex Brief — Marketplace Intelligence v1

**Sprint:** 1.7  
**Status:** APPROVED — ready for implementation  
**Author:** HYDRA Chief Architect  
**Date:** 2026-05-10  
**Preceded by:** Sprint 1.5.1 (LLM Observability + UX Polish)  
**Followed by:** Sprint 4.0 (Gumroad publishing automation)

---

## Purpose of This Document

This brief is **fully self-contained**. Codex (or any engineer) must be able to implement
Sprint 1.7 in its entirety using only this document + the existing codebase. No additional
context, no oral instructions, no guesswork required.

If Claude becomes unavailable mid-sprint, Codex continues from this brief.

---

## Objective

Give HYDRA the ability to:

1. Ingest curated marketplace research (manual entry or CSV upload)
2. Extract winning product patterns from that research via guarded LLM analysis
3. Generate opportunity candidates from those patterns
4. Surface candidates in the existing operator approval UI

**Operator approves at every gate. Nothing publishes automatically.**

This sprint does NOT build scraping, Etsy API integration, image generation,
Celery scheduling, or auto-publishing. See Do-Not-Build list.

---

## Architectural Constraints (read before touching any file)

- **Zone A / Zone B boundary is sacred.** Zone A = LLM generation only, produces
  artifacts only. Zone B = FastAPI + Postgres, owns state, money, approvals. Never cross.
- All external HTTP calls in routes are FORBIDDEN. The CSV import reads operator-provided
  data only. No requests to Etsy, Reddit, or any external service from any new route.
- All LLM calls go through `app/llm.py:call_llm_json()`. Never call a provider directly.
- All DB changes require an Alembic migration. Never use `Base.metadata.create_all()` for
  new tables.
- Flash messages use the query-string pattern: redirect to `?flash=success&step=X`.
- `PASS=$((PASS+1))` in bash verify scripts — NEVER `((PASS++))` (exits with code 1 when PASS=0).


---

## DB Schema — 3 New Tables

### Migration file
`app/alembic/versions/0003_sprint17_market_intelligence.py`

```python
"""Sprint 1.7 — Marketplace Intelligence tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_research_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False, server_default="manual"),
        sa.Column("category", sa.Text),
        sa.Column("query", sa.Text),
        sa.Column("item_count", sa.Integer, server_default="0"),
        sa.Column("status", sa.Text, nullable=False, server_default="raw"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "market_research_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer,
                  sa.ForeignKey("market_research_runs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("shop_name", sa.Text),
        sa.Column("price_cents", sa.Integer),
        sa.Column("currency", sa.Text, server_default="USD"),
        sa.Column("rating", sa.Numeric(3, 2)),
        sa.Column("review_count", sa.Integer),
        sa.Column("tags", sa.Text),
        sa.Column("listing_url", sa.Text),
        sa.Column("product_type", sa.Text),
        sa.Column("aesthetic", sa.Text),
        sa.Column("bundle_type", sa.Text),
        sa.Column("pain_point", sa.Text),
        sa.Column("pattern_notes", sa.Text),
        sa.Column("risk_flags", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_market_research_items_run_id",
        "market_research_items", ["run_id"]
    )

    op.create_table(
        "market_patterns",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.Integer,
                  sa.ForeignKey("market_research_runs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("pattern_type", sa.Text, nullable=False),
        sa.Column("pattern_summary", sa.Text, nullable=False),
        sa.Column("example_titles", sa.Text),
        sa.Column("price_range_low", sa.Integer),
        sa.Column("price_range_high", sa.Integer),
        sa.Column("recommended_modality", sa.Text),
        sa.Column("recommended_marketplace", sa.Text),
        sa.Column("confidence", sa.Text, server_default="medium"),
        sa.Column("used_for_opportunity_id", sa.Integer,
                  sa.ForeignKey("opportunity_candidates.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_market_patterns_run_id",
        "market_patterns", ["run_id"]
    )


def downgrade() -> None:
    op.drop_table("market_patterns")
    op.drop_table("market_research_items")
    op.drop_table("market_research_runs")
```


---

## SQLAlchemy Models (add to `app/db.py`)

Add these three models. Import `Numeric` from `sqlalchemy`. Add to `_apply_one_shot_migrations()`
as CREATE TABLE IF NOT EXISTS safety nets (same pattern as `listings` table).

```python
class MarketResearchRun(Base):
    __tablename__ = "market_research_runs"
    id          = Column(Integer, primary_key=True)
    label       = Column(Text, nullable=False)
    source      = Column(Text, nullable=False, default="manual")
    category    = Column(Text)
    query       = Column(Text)
    item_count  = Column(Integer, default=0)
    # status: raw | analyzed | archived
    status      = Column(Text, nullable=False, default="raw")
    notes       = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())
    items       = relationship("MarketResearchItem", back_populates="run",
                               cascade="all, delete-orphan")
    patterns    = relationship("MarketPattern", back_populates="run",
                               cascade="all, delete-orphan")


class MarketResearchItem(Base):
    __tablename__ = "market_research_items"
    id            = Column(Integer, primary_key=True)
    run_id        = Column(Integer, ForeignKey("market_research_runs.id",
                           ondelete="CASCADE"), nullable=False)
    title         = Column(Text, nullable=False)
    shop_name     = Column(Text)
    price_cents   = Column(Integer)
    currency      = Column(Text, default="USD")
    rating        = Column(Numeric(3, 2))
    review_count  = Column(Integer)
    tags          = Column(Text)          # comma-separated string
    listing_url   = Column(Text)          # stored only — never fetched
    # product_type: printable | planner | canva_template | prompt_pack |
    #               pod_design | checklist | worksheet | tracker |
    #               social_kit | bundle | other
    product_type  = Column(Text)
    aesthetic     = Column(Text)          # minimalist | boho | colorful | professional | etc.
    bundle_type   = Column(Text)          # single | bundle | kit | collection
    pain_point    = Column(Text)
    pattern_notes = Column(Text)
    risk_flags    = Column(Text)
    created_at    = Column(DateTime, server_default=func.now())
    run           = relationship("MarketResearchRun", back_populates="items")


class MarketPattern(Base):
    __tablename__ = "market_patterns"
    id                       = Column(Integer, primary_key=True)
    run_id                   = Column(Integer, ForeignKey("market_research_runs.id",
                                      ondelete="CASCADE"), nullable=False)
    # pattern_type: title_structure | tag_cluster | pricing_range |
    #               bundle_pattern | pain_point | underserved_angle |
    #               modality_recommendation | marketplace_recommendation
    pattern_type             = Column(Text, nullable=False)
    pattern_summary          = Column(Text, nullable=False)
    example_titles           = Column(Text)   # JSON array stored as text
    price_range_low          = Column(Integer)   # cents
    price_range_high         = Column(Integer)   # cents
    recommended_modality     = Column(Text)
    recommended_marketplace  = Column(Text)
    # confidence: low | medium | high
    confidence               = Column(Text, default="medium")
    used_for_opportunity_id  = Column(Integer, ForeignKey("opportunity_candidates.id",
                                      ondelete="SET NULL"), nullable=True)
    created_at               = Column(DateTime, server_default=func.now())
    run                      = relationship("MarketResearchRun", back_populates="patterns")
```

Also add to `_apply_one_shot_migrations()`:
```python
"""CREATE TABLE IF NOT EXISTS market_research_runs (
    id SERIAL PRIMARY KEY, label TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual', category TEXT, query TEXT,
    item_count INTEGER DEFAULT 0, status TEXT NOT NULL DEFAULT 'raw',
    notes TEXT, created_at TIMESTAMP DEFAULT now(), updated_at TIMESTAMP DEFAULT now()
)""",
"""CREATE TABLE IF NOT EXISTS market_research_items (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES market_research_runs(id) ON DELETE CASCADE,
    title TEXT NOT NULL, shop_name TEXT, price_cents INTEGER, currency TEXT DEFAULT 'USD',
    rating NUMERIC(3,2), review_count INTEGER, tags TEXT, listing_url TEXT,
    product_type TEXT, aesthetic TEXT, bundle_type TEXT, pain_point TEXT,
    pattern_notes TEXT, risk_flags TEXT, created_at TIMESTAMP DEFAULT now()
)""",
"CREATE INDEX IF NOT EXISTS ix_market_research_items_run_id ON market_research_items (run_id)",
"""CREATE TABLE IF NOT EXISTS market_patterns (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES market_research_runs(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL, pattern_summary TEXT NOT NULL,
    example_titles TEXT, price_range_low INTEGER, price_range_high INTEGER,
    recommended_modality TEXT, recommended_marketplace TEXT,
    confidence TEXT DEFAULT 'medium',
    used_for_opportunity_id INTEGER REFERENCES opportunity_candidates(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT now()
)""",
"CREATE INDEX IF NOT EXISTS ix_market_patterns_run_id ON market_patterns (run_id)",
```


---

## Routes (add to `app/main.py`)

All imports needed: `csv`, `io`, `json` (stdlib). `UploadFile`, `File` from fastapi.

### 1. List runs

```python
@app.get("/market-research")
def market_research_list(request: Request):
    with Session(engine) as session:
        runs = session.scalars(
            select(MarketResearchRun).order_by(desc(MarketResearchRun.created_at))
        ).all()
    return templates.TemplateResponse("market_research_list.html",
        {"request": request, "runs": runs})
```

### 2. New run form

```python
@app.get("/market-research/new")
def market_research_new(request: Request):
    return templates.TemplateResponse("market_research_detail.html",
        {"request": request, "run": None, "items": [], "patterns": []})
```

### 3. Create run

```python
@app.post("/market-research")
def market_research_create(request: Request,
    label: str = Form(...),
    category: str = Form(""),
    query: str = Form(""),
    notes: str = Form(""),
):
    with Session(engine) as session:
        run = MarketResearchRun(
            label=label.strip(),
            category=category.strip() or None,
            query=query.strip() or None,
            notes=notes.strip() or None,
        )
        session.add(run)
        session.commit()
        run_id = run.id
    return RedirectResponse(url=f"/market-research/{run_id}", status_code=303)
```

### 4. View run detail

```python
@app.get("/market-research/{run_id}")
def market_research_detail(request: Request, run_id: int,
    flash: str = "", msg: str = "", page: int = 1,
):
    with Session(engine) as session:
        run = session.get(MarketResearchRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        page_size = 25
        offset = (page - 1) * page_size
        items = session.scalars(
            select(MarketResearchItem)
            .where(MarketResearchItem.run_id == run_id)
            .order_by(MarketResearchItem.id)
            .offset(offset).limit(page_size)
        ).all()
        total_items = session.scalar(
            select(func.count(MarketResearchItem.id))
            .where(MarketResearchItem.run_id == run_id)
        ) or 0
        patterns = session.scalars(
            select(MarketPattern).where(MarketPattern.run_id == run_id)
            .order_by(MarketPattern.pattern_type)
        ).all()
        flash_banner = None
        if flash == "success":
            flash_banner = {"level": "success", "message": msg or "Done."}
        elif flash == "error":
            flash_banner = {"level": "error", "message": msg or "Error."}
    return templates.TemplateResponse("market_research_detail.html", {
        "request": request, "run": run, "items": items, "patterns": patterns,
        "flash_banner": flash_banner, "page": page, "page_size": page_size,
        "total_items": total_items, "total_pages": max(1, -(-total_items // page_size)),
    })
```

### 5. CSV import

```python
@app.post("/market-research/{run_id}/import-csv")
async def market_research_import_csv(run_id: int, file: UploadFile = File(...)):
    ALLOWED_COLS = {
        "title", "shop_name", "price", "currency", "rating", "review_count",
        "tags", "listing_url", "product_type", "aesthetic", "bundle_type",
        "pain_point", "pattern_notes", "risk_flags",
    }
    contents = await file.read()
    text = contents.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    imported = 0
    errors = []
    with Session(engine) as session:
        run = session.get(MarketResearchRun, run_id)
        if not run:
            raise HTTPException(status_code=404)
        for i, row in enumerate(reader, start=1):
            title = (row.get("title") or "").strip()
            if not title:
                errors.append(f"Row {i}: missing title — skipped")
                continue
            price_raw = (row.get("price") or "").strip().replace("$", "").replace(",", "")
            try:
                price_cents = int(float(price_raw) * 100) if price_raw else None
            except ValueError:
                price_cents = None
            rating_raw = (row.get("rating") or "").strip()
            try:
                rating = float(rating_raw) if rating_raw else None
            except ValueError:
                rating = None
            review_raw = (row.get("review_count") or "").strip().replace(",", "")
            try:
                review_count = int(review_raw) if review_raw else None
            except ValueError:
                review_count = None
            item = MarketResearchItem(
                run_id=run_id,
                title=title,
                shop_name=(row.get("shop_name") or "").strip() or None,
                price_cents=price_cents,
                currency=(row.get("currency") or "USD").strip().upper() or "USD",
                rating=rating,
                review_count=review_count,
                tags=(row.get("tags") or "").strip() or None,
                listing_url=(row.get("listing_url") or "").strip() or None,
                product_type=(row.get("product_type") or "").strip() or None,
                aesthetic=(row.get("aesthetic") or "").strip() or None,
                bundle_type=(row.get("bundle_type") or "").strip() or None,
                pain_point=(row.get("pain_point") or "").strip() or None,
                pattern_notes=(row.get("pattern_notes") or "").strip() or None,
                risk_flags=(row.get("risk_flags") or "").strip() or None,
            )
            session.add(item)
            imported += 1
        run.item_count = session.scalar(
            select(func.count(MarketResearchItem.id))
            .where(MarketResearchItem.run_id == run_id)
        ) or 0
        session.commit()
    msg = f"Imported {imported} items."
    if errors:
        msg += f" {len(errors)} rows skipped: " + "; ".join(errors[:3])
    return RedirectResponse(
        url=f"/market-research/{run_id}?flash=success&msg={msg}", status_code=303
    )
```


### 6. Analyze — extract patterns via guarded LLM

```python
@app.post("/market-research/{run_id}/analyze")
def market_research_analyze(run_id: int):
    with Session(engine) as session:
        run = session.get(MarketResearchRun, run_id)
        if not run:
            raise HTTPException(status_code=404)
        items = session.scalars(
            select(MarketResearchItem).where(MarketResearchItem.run_id == run_id)
        ).all()
        if not items:
            return RedirectResponse(
                url=f"/market-research/{run_id}?flash=error&msg=No+items+to+analyze",
                status_code=303
            )
        # Build item summaries for LLM (no PII, no full URLs)
        item_summaries = []
        for it in items:
            parts = [f"Title: {it.title}"]
            if it.price_cents:
                parts.append(f"Price: ${it.price_cents/100:.2f}")
            if it.rating:
                parts.append(f"Rating: {it.rating}")
            if it.review_count:
                parts.append(f"Reviews: {it.review_count}")
            if it.tags:
                parts.append(f"Tags: {it.tags}")
            if it.product_type:
                parts.append(f"Type: {it.product_type}")
            if it.aesthetic:
                parts.append(f"Aesthetic: {it.aesthetic}")
            if it.bundle_type:
                parts.append(f"Bundle: {it.bundle_type}")
            if it.pain_point:
                parts.append(f"Pain point: {it.pain_point}")
            if it.pattern_notes:
                parts.append(f"Notes: {it.pattern_notes}")
            item_summaries.append(" | ".join(parts))

        # Batch into groups of 30
        BATCH_SIZE = 30
        all_patterns_raw = []
        for batch_start in range(0, len(item_summaries), BATCH_SIZE):
            batch = item_summaries[batch_start: batch_start + BATCH_SIZE]
            batch_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(batch))
            prompt = f"""You are a marketplace product analyst. Analyze the following
{len(batch)} digital product listings and extract winning patterns.

LISTINGS:
{batch_text}

Return a JSON object with this exact structure:
{{
  "patterns": [
    {{
      "pattern_type": "title_structure | tag_cluster | pricing_range | bundle_pattern | pain_point | underserved_angle | modality_recommendation | marketplace_recommendation",
      "pattern_summary": "Clear 1-3 sentence description of the pattern",
      "example_titles": ["title1", "title2"],
      "price_range_low": null or integer cents (e.g. 500 = $5.00),
      "price_range_high": null or integer cents,
      "recommended_modality": null or "printable | planner | canva_template | prompt_pack | pod_design | checklist | worksheet | tracker | social_kit | bundle | other",
      "recommended_marketplace": null or "etsy | gumroad | creative_market | payhip | sellfy",
      "confidence": "low | medium | high"
    }}
  ]
}}

RULES:
- Extract structural patterns only. Do NOT reproduce or describe specific seller shops.
- Do NOT recommend copying any listing. Patterns must be generalizable.
- Focus on: what title structures appear repeatedly, what tags cluster together,
  what price points dominate, what buyer pain points recur, what product modalities
  appear underserved relative to demand signals.
- Return 5 to 15 patterns. More is better if well-supported.
- If a pattern is speculative, set confidence to "low".
- Return valid JSON only. No markdown, no explanation outside the JSON."""

            result = call_llm_json(prompt, purpose="market_pattern_extraction")
            if isinstance(result, dict) and "patterns" in result:
                all_patterns_raw.extend(result["patterns"])

        # Persist patterns
        # Delete existing patterns for this run first (idempotent re-analysis)
        session.execute(
            sa.delete(MarketPattern).where(MarketPattern.run_id == run_id)
        )
        added = 0
        for p in all_patterns_raw:
            if not p.get("pattern_summary"):
                continue
            pattern = MarketPattern(
                run_id=run_id,
                pattern_type=p.get("pattern_type", "unknown"),
                pattern_summary=p["pattern_summary"],
                example_titles=json.dumps(p.get("example_titles") or []),
                price_range_low=p.get("price_range_low"),
                price_range_high=p.get("price_range_high"),
                recommended_modality=p.get("recommended_modality"),
                recommended_marketplace=p.get("recommended_marketplace"),
                confidence=p.get("confidence", "medium"),
            )
            session.add(pattern)
            added += 1
        run.status = "analyzed"
        session.commit()

    return RedirectResponse(
        url=f"/market-research/{run_id}?flash=success&msg=Extracted+{added}+patterns",
        status_code=303
    )
```

### 7. Generate opportunities from patterns

```python
@app.post("/market-research/{run_id}/generate-opportunities")
def market_research_generate_opportunities(run_id: int):
    with Session(engine) as session:
        run = session.get(MarketResearchRun, run_id)
        if not run:
            raise HTTPException(status_code=404)
        patterns = session.scalars(
            select(MarketPattern)
            .where(MarketPattern.run_id == run_id)
            .where(MarketPattern.confidence.in_(["medium", "high"]))
            .where(MarketPattern.used_for_opportunity_id.is_(None))
        ).all()
        if not patterns:
            return RedirectResponse(
                url=f"/market-research/{run_id}?flash=error&msg=No+unused+medium/high+patterns",
                status_code=303
            )

        pattern_text = "\n".join(
            f"- [{p.pattern_type}] {p.pattern_summary}"
            + (f" | Modality: {p.recommended_modality}" if p.recommended_modality else "")
            + (f" | Marketplace: {p.recommended_marketplace}" if p.recommended_marketplace else "")
            + (f" | Price range: ${(p.price_range_low or 0)/100:.0f}–${(p.price_range_high or 0)/100:.0f}" if p.price_range_low else "")
            for p in patterns
        )
        prompt = f"""You are a digital product strategist for an indie creator.
Based on the following marketplace patterns extracted from real market research,
generate 3 to 5 original digital product opportunity ideas.

PATTERNS:
{pattern_text}

Return a JSON object:
{{
  "opportunities": [
    {{
      "topic": "Specific product concept title (not a copy of any existing listing)",
      "modality": "printable | planner | canva_template | prompt_pack | pod_design | checklist | worksheet | tracker | social_kit | bundle | other",
      "marketplace": "etsy | gumroad | creative_market | payhip | sellfy",
      "differentiation": "1-2 sentences: what makes this distinct and original",
      "target_buyer": "who this is for",
      "price_point_dollars": null or integer,
      "pattern_basis": "which pattern(s) inspired this"
    }}
  ]
}}

RULES:
- Each opportunity must be a NEW, ORIGINAL concept. Do not describe or copy any real listing.
- Ideas must be legal, non-infringing, and ethically producible.
- Prefer underserved angles over saturated categories.
- Return valid JSON only."""

        result = call_llm_json(prompt, purpose="market_opportunity_generation")
        opps = result.get("opportunities", []) if isinstance(result, dict) else []

        created_ids = []
        for opp in opps:
            if not opp.get("topic"):
                continue
            notes = (
                f"Modality: {opp.get('modality', 'unknown')} | "
                f"Marketplace: {opp.get('marketplace', 'unknown')} | "
                f"Differentiation: {opp.get('differentiation', '')} | "
                f"Target buyer: {opp.get('target_buyer', '')} | "
                f"Pattern basis: {opp.get('pattern_basis', '')} | "
                f"Price: ${opp.get('price_point_dollars', '?')}"
            )
            candidate = OpportunityCandidate(
                topic=opp["topic"][:500],
                source="market_intelligence",
                evidence=notes[:1000],
                status="pending_review",
            )
            session.add(candidate)
            session.flush()
            created_ids.append(candidate.id)
            # Link first pattern to this opportunity (informational)
            if patterns:
                patterns[0].used_for_opportunity_id = candidate.id

        session.commit()

    return RedirectResponse(
        url=f"/market-research/{run_id}?flash=success&msg=Created+{len(created_ids)}+opportunities+for+review",
        status_code=303
    )
```

### 8. Delete/archive run

```python
@app.post("/market-research/{run_id}/delete")
def market_research_delete(run_id: int):
    with Session(engine) as session:
        run = session.get(MarketResearchRun, run_id)
        if run:
            session.delete(run)
            session.commit()
    return RedirectResponse(url="/market-research?flash=success&msg=Run+deleted",
                            status_code=303)
```

**Note:** Use POST (not DELETE) for delete — HTML forms only support GET/POST.
Add `flash` query param handling to the list route the same way as detail route.


---

## CSV Import Format

Operator-facing documentation. Include this in the UI as a download link or inline help text.

**Required column:** `title`

**Optional columns:**

| Column | Format | Example |
|---|---|---|
| `shop_name` | text | `PlannerQueenShop` |
| `price` | decimal dollars | `7.99` |
| `currency` | 3-letter code | `USD` |
| `rating` | decimal 0–5 | `4.8` |
| `review_count` | integer | `1247` |
| `tags` | comma-separated | `planner,printable,adhd,student` |
| `listing_url` | URL | `https://etsy.com/listing/...` |
| `product_type` | see enum | `planner` |
| `aesthetic` | text | `minimalist` |
| `bundle_type` | single/bundle/kit/collection | `bundle` |
| `pain_point` | text | `overwhelm, forgetting tasks` |
| `pattern_notes` | operator notes | `Strong seasonal demand` |
| `risk_flags` | text | `branded keyword: ADHD Focus` |

**product_type enum:** `printable | planner | canva_template | prompt_pack | pod_design |
checklist | worksheet | tracker | social_kit | bundle | other`

**Example CSV (include as `sample_research.csv` in `scripts/`):**
```csv
title,shop_name,price,rating,review_count,tags,product_type,aesthetic,bundle_type,pain_point
ADHD Student Planner Bundle Printable,PlannerHub,8.99,4.9,2341,"planner,adhd,student,printable,focus",planner,minimalist,bundle,forgetting tasks overwhelm
Minimal Weekly Reset Planner A5,CleanPlanners,5.99,4.7,892,"planner,minimalist,weekly,reset,a5",planner,minimalist,single,lack of weekly structure
Canva Social Media Kit for Coaches,CoachTemplates,19.99,4.8,445,"canva,social media,coach,instagram,template",canva_template,professional,kit,inconsistent branding
```

---

## Templates

### `app/templates/market_research_list.html`

Extends base layout. Shows a table of runs with columns:
- Label (linked to `/market-research/{id}`)
- Category
- Source badge (manual = gray, csv = blue, etsy_api = green)
- Status badge (raw = gray, analyzed = yellow, archived = dark)
- Items count
- Patterns count
- Created date (`%Y-%m-%d`)
- Actions: View, Delete (POST form with confirm)

Top of page: "New Research Run" button → `/market-research/new`

Flash banner at top (reuse existing flash_banner pattern from product_edit.html).

Empty state: "No research runs yet. Start by creating a new run."

### `app/templates/market_research_detail.html`

Two modes: `run is None` (new run form) and `run exists` (detail view).

**New run form** (when `run is None`):
- Fields: Label (required), Category, Search Query, Notes
- Submit: POST `/market-research`
- Cancel: back to list

**Detail view** (when `run` exists):

Section 1 — Run info bar:
- Label, category, source, status badge, created date, item count, pattern count
- Edit notes inline (small form, POST to `/market-research/{id}` with `_method=PATCH`
  — or simplify: just show notes as text with an edit button that reveals a form)

Section 2 — CSV Import:
- `<form enctype="multipart/form-data" action="/market-research/{id}/import-csv" method="post">`
- File input (accept `.csv`)
- Submit button: "Import CSV"
- Link: "Download sample CSV" → `/static/sample_research.csv` (or inline the sample)

Section 3 — Items table (paginated 25/page):
Columns: Title (truncated 60 chars), Shop, Price, Rating, Reviews, Type, Aesthetic, Bundle,
Pain Point (truncated 40 chars), Risk Flags (red badge if present), Notes icon (hover for full)

Pagination: Previous / Page N of M / Next

Section 4 — Actions:
- "Analyze Patterns" button (POST `/market-research/{id}/analyze`) — disabled if item_count == 0
- "Generate Opportunities" button (POST `/market-research/{id}/generate-opportunities`) — disabled if status != "analyzed"
- Both buttons show a spinner on click (use `onclick="this.disabled=true;this.form.submit()"`)

Section 5 — Patterns (shown after analysis):
Table with columns: Type (badge), Summary, Example Titles (collapsed), Modality, Marketplace,
Price Range, Confidence (color-coded: green=high, yellow=medium, red=low), Used?

If no patterns yet: "Run analysis to extract patterns."

Flash banner at top (same pattern as product_edit.html).

---

## Nav Link

Add to the main navigation (base template or wherever nav links live):
```html
<a href="/market-research">Market Research</a>
```

---

## LLM Prompt Notes for Claude (not Codex)

The two prompts above (pattern extraction and opportunity generation) were designed with
these constraints:

**Pattern extraction prompt:**
- Explicitly forbids reproducing shop names or copying listings
- Asks for structural/generalizable patterns only
- Requests confidence scoring so low-signal patterns are filtered before opportunity generation
- Batches at 30 items to stay within typical context windows
- Re-analysis is idempotent: deletes existing patterns before inserting new ones

**Opportunity generation prompt:**
- Takes only patterns as input (not raw items — one level of abstraction away from real listings)
- Explicitly requires "NEW, ORIGINAL concept"
- Requests differentiation rationale per opportunity
- Filtered to medium/high confidence patterns only
- Max ~15 patterns in prompt (filtered from potentially 30+)

**If pattern extraction produces garbage:** Check that `call_llm_json` is returning a dict,
not a string. The route handles this: `if isinstance(result, dict) and "patterns" in result`.
If the LLM returns malformed JSON, `call_llm_json` should raise `bad_json` error type and
log it. The route will then produce 0 patterns and redirect with a success message showing
"Extracted 0 patterns" — which is the signal to inspect the LLM call log in Settings.


---

## Verify Script — `scripts/verify_sprint17.sh`

```bash
#!/usr/bin/env bash
# verify_sprint17.sh — Sprint 1.7 Marketplace Intelligence v1
# Usage:
#   bash scripts/verify_sprint17.sh          # static checks only
#   LIVE=1 bash scripts/verify_sprint17.sh   # + live checks (needs running stack)
set -euo pipefail
HYDRA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HYDRA_ROOT"
PASS=0; FAIL=0
BASE="${BASE:-http://localhost:8000}"
AUTH=""
pass() { echo "PASS  $1"; PASS=$((PASS+1)); }
fail() { echo "FAIL  $1"; FAIL=$((FAIL+1)); }

echo "=== Sprint 1.7 — Static checks ==="

# Migration
[ -f "app/alembic/versions/0003_sprint17_market_intelligence.py" ] \
  && pass "migration: 0003 file exists" || fail "migration: 0003 file missing"
grep -q "market_research_runs" app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: creates market_research_runs" || fail "migration: missing market_research_runs"
grep -q "market_research_items" app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: creates market_research_items" || fail "migration: missing market_research_items"
grep -q "market_patterns" app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: creates market_patterns" || fail "migration: missing market_patterns"
grep -q "down_revision.*=.*\"0002\"\|down_revision.*=.*'0002'" \
  app/alembic/versions/0003_sprint17_market_intelligence.py \
  && pass "migration: down_revision is 0002" || fail "migration: wrong down_revision"

# Models
grep -q "class MarketResearchRun" app/db.py \
  && pass "db.py: MarketResearchRun model" || fail "db.py: MarketResearchRun missing"
grep -q "class MarketResearchItem" app/db.py \
  && pass "db.py: MarketResearchItem model" || fail "db.py: MarketResearchItem missing"
grep -q "class MarketPattern" app/db.py \
  && pass "db.py: MarketPattern model" || fail "db.py: MarketPattern missing"
grep -q "market_research_runs.*IF NOT EXISTS\|IF NOT EXISTS.*market_research_runs" app/db.py \
  && pass "db.py: market_research_runs safety net" || fail "db.py: safety net missing"

# Routes
grep -q "/market-research" app/main.py \
  && pass "main.py: market-research routes present" || fail "main.py: market-research routes missing"
grep -q "import-csv\|import_csv" app/main.py \
  && pass "main.py: CSV import route present" || fail "main.py: CSV import route missing"
grep -q "market_pattern_extraction" app/main.py \
  && pass "main.py: pattern extraction purpose string present" || fail "main.py: purpose string missing"
grep -q "market_opportunity_generation" app/main.py \
  && pass "main.py: opportunity generation purpose string present" || fail "main.py: purpose string missing"
grep -q "source.*market_intelligence\|market_intelligence.*source" app/main.py \
  && pass "main.py: opportunity source=market_intelligence" || fail "main.py: source tag missing"

# Templates
[ -f "app/templates/market_research_list.html" ] \
  && pass "templates: market_research_list.html exists" || fail "templates: list template missing"
[ -f "app/templates/market_research_detail.html" ] \
  && pass "templates: market_research_detail.html exists" || fail "templates: detail template missing"
grep -q "import-csv\|import_csv" app/templates/market_research_detail.html \
  && pass "template: CSV import form present" || fail "template: CSV import form missing"
grep -q "analyze\|Analyze" app/templates/market_research_detail.html \
  && pass "template: Analyze button present" || fail "template: Analyze button missing"
grep -q "generate-opportunities\|generate_opportunities" app/templates/market_research_detail.html \
  && pass "template: Generate Opportunities button present" || fail "template: Generate Opportunities button missing"

# No external HTTP calls in routes
! grep -qP "requests\.(get|post|put|delete)|httpx\.(get|post)|aiohttp" app/main.py \
  && pass "main.py: no raw external HTTP calls" || fail "main.py: contains raw HTTP calls — use call_llm_json only"

# Syntax
python3 -m py_compile app/db.py   && pass "syntax: db.py OK"   || fail "syntax: db.py ERROR"
python3 -m py_compile app/main.py && pass "syntax: main.py OK" || fail "syntax: main.py ERROR"

echo ""
echo "=== Static results: PASS=$PASS FAIL=$FAIL ==="
echo ""

if [ "${LIVE:-0}" != "1" ]; then
  echo "(Skipping live checks. Set LIVE=1 to run.)"
  exit $( [ "$FAIL" -eq 0 ] && echo 0 || echo 1 )
fi

echo "=== Sprint 1.7 — Live checks ==="

# Create a run
response=$(curl -si $AUTH -d "label=Test+Run+1.7&category=planners&query=planner&notes=" \
  "$BASE/market-research" --max-redirs 0 2>/dev/null || true)
location=$(echo "$response" | grep -i "^Location:" | head -1 | tr -d '\r')
run_id=$(echo "$location" | grep -oP '(?<=/market-research/)\d+' | head -1 || echo "")
[ -n "$run_id" ] \
  && pass "live: create run → 303 to /market-research/$run_id" \
  || fail "live: create run failed — location='$location'"

if [ -n "$run_id" ]; then
  # List page renders new run
  list_html=$(curl -sf $AUTH "$BASE/market-research" 2>/dev/null || echo "")
  echo "$list_html" | grep -qi "Test Run 1.7" \
    && pass "live: list page shows new run" \
    || fail "live: list page missing new run"

  # Detail page renders
  detail_html=$(curl -sf $AUTH "$BASE/market-research/$run_id" 2>/dev/null || echo "")
  echo "$detail_html" | grep -qi "Import CSV\|import.csv\|import_csv" \
    && pass "live: detail page renders CSV import form" \
    || fail "live: detail page missing CSV import form"

  # CSV import
  CSV_FILE=$(mktemp /tmp/test_XXXXXX.csv)
  printf 'title,shop_name,price,rating,review_count,tags,product_type\n' > "$CSV_FILE"
  printf 'ADHD Focus Planner Bundle,TestShop,8.99,4.9,500,"planner,adhd,focus",planner\n' >> "$CSV_FILE"
  printf 'Minimal Weekly Tracker Printable,TestShop2,5.99,4.7,200,"tracker,weekly,minimal",tracker\n' >> "$CSV_FILE"
  printf 'Canva Social Kit for Coaches,TestShop3,19.99,4.8,100,"canva,social,coach",canva_template\n' >> "$CSV_FILE"

  import_response=$(curl -si $AUTH -F "file=@$CSV_FILE;type=text/csv" \
    "$BASE/market-research/$run_id/import-csv" --max-redirs 0 2>/dev/null || true)
  import_location=$(echo "$import_response" | grep -i "^Location:" | head -1 | tr -d '\r')
  echo "$import_location" | grep -qi "success\|flash" \
    && pass "live: CSV import → redirect with success flash" \
    || fail "live: CSV import → unexpected redirect: $import_location"
  rm -f "$CSV_FILE"

  # Items appear on detail page
  detail_after=$(curl -sf $AUTH "$BASE/market-research/$run_id" 2>/dev/null || echo "")
  echo "$detail_after" | grep -qi "ADHD Focus Planner\|TestShop\|Canva Social" \
    && pass "live: imported items appear on detail page" \
    || fail "live: imported items not visible on detail page"

  # Analyze (requires LLM — may fail if no key; just check redirect)
  analyze_response=$(curl -si $AUTH -d "" "$BASE/market-research/$run_id/analyze" \
    --max-redirs 0 2>/dev/null || true)
  analyze_code=$(echo "$analyze_response" | grep -oP "^HTTP/\S+ \K\d+" | head -1 || echo "0")
  [ "$analyze_code" = "303" ] \
    && pass "live: analyze → 303 redirect (LLM call attempted)" \
    || fail "live: analyze returned HTTP $analyze_code instead of 303"

  # Opportunities page shows market_intelligence source badge
  opps_html=$(curl -sf $AUTH "$BASE/opportunities" 2>/dev/null || echo "")
  # Opportunities may or may not exist depending on LLM; just check page renders
  echo "$opps_html" | grep -qi "opportunities\|Opportunities\|opportunity" \
    && pass "live: /opportunities page renders" \
    || fail "live: /opportunities page broken"
fi

echo ""
echo "=== Final: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ] && echo "✅ All checks passed." || echo "❌ $FAIL check(s) failed."
exit $( [ "$FAIL" -eq 0 ] && echo 0 || echo 1 )
```


---

## Acceptance Criteria

Sprint 1.7 is complete when ALL of the following are true:

- [ ] `bash scripts/verify_sprint17.sh` exits 0 (all static checks pass)
- [ ] `LIVE=1 bash scripts/verify_sprint17.sh` exits 0 (all live checks pass)
- [ ] `alembic upgrade head` from `0002` applies `0003` without error
- [ ] `alembic downgrade 0002` drops `market_patterns`, `market_research_items`,
      `market_research_runs` cleanly (in that order due to FK constraints)
- [ ] Creating a run, importing a 3-row CSV, and running Analyze produces at least
      1 `market_patterns` row (requires a valid LLM API key)
- [ ] "Generate Opportunities" creates candidates visible in `/opportunities`
      with `source = market_intelligence`
- [ ] No opportunity moves past `pending_review` without operator action
- [ ] No external HTTP requests are made by any new route (verified by grep in verify script)
- [ ] `python3 -m py_compile app/db.py app/main.py` passes with no errors
- [ ] Nav link to `/market-research` appears in the console UI

---

## Do-Not-Build List

Do NOT implement any of the following in Sprint 1.7:

| Item | Reason / When |
|---|---|
| Etsy Open API v3 OAuth | Requires Etsy app review; Sprint 8.x |
| Automated Etsy listing scraper | Platform ToS risk; manual import is sufficient for v1 |
| Printify / Printful / Gelato integration | Sprint 7.5, after marketplace publishing works |
| Celery + Redis scheduler | Sprint 8.x; no long-running jobs needed here |
| Reddit collector | Lower signal quality; deferred to Sprint 8.x |
| Image generation | Sprint 8.x; blocked until modality model proven |
| Vector embeddings / semantic search | Premature; LLM extraction sufficient for v1 |
| Auto-publishing to any marketplace | Requires operator approval; never automated |
| Copying or reformulating real listings | Violates Etsy ToS and operator's explicit constraint |
| Paid third-party research APIs (Marmalead, eRank) | Evaluate in Sprint 8.x |
| Dashboard redesign | Scope creep |
| User accounts / auth | Out of scope entirely |

---

## Rollback Notes

If Sprint 1.7 needs to be rolled back:

```bash
# 1. Downgrade DB
docker compose exec hydra-console alembic downgrade 0002

# 2. Revert code to pre-Sprint-1.7 commit
git revert HEAD  # or git checkout <pre-sprint-commit>

# 3. Restart container
docker compose restart hydra-console

# 4. Verify
bash scripts/verify_sprint16.sh
bash scripts/verify_sprint151.sh
```

The downgrade migration drops all 3 new tables cleanly. No data loss to existing tables.
The `opportunity_candidates` rows with `source = market_intelligence` will be orphaned
after downgrade — delete them manually if needed:
```sql
DELETE FROM opportunity_candidates WHERE source = 'market_intelligence';
```

---

## Files to Create / Modify

```
CREATE  app/alembic/versions/0003_sprint17_market_intelligence.py
MODIFY  app/db.py           — add 3 models, safety nets in _apply_one_shot_migrations
MODIFY  app/main.py         — add 8 routes, import csv/io/json
CREATE  app/templates/market_research_list.html
CREATE  app/templates/market_research_detail.html
CREATE  scripts/verify_sprint17.sh
CREATE  scripts/sample_research.csv
MODIFY  runbooks/ROADMAP.md — update Sprint 1.7 description
```

---

## Codex Execution Order

Codex should implement in this order to avoid import/dependency errors:

1. Migration file (`0003_sprint17_market_intelligence.py`) — no dependencies
2. `app/db.py` — models + safety nets (depends on migration being written first for reference)
3. `app/main.py` — routes (depends on models)
4. `app/templates/market_research_list.html` — depends on route signatures
5. `app/templates/market_research_detail.html` — depends on route signatures
6. `scripts/verify_sprint17.sh` — depends on all of the above
7. `scripts/sample_research.csv` — standalone
8. `runbooks/ROADMAP.md` — update Sprint 1.7 entry

Run `bash scripts/verify_sprint17.sh` after step 6. Fix any failures before proceeding.
Run `LIVE=1 bash scripts/verify_sprint17.sh` after the stack is confirmed running.

---

## Human Approval Gates (unchanged from existing flow)

1. Operator reviews opportunity candidates in `/opportunities` UI
2. Operator approves or rejects each candidate — no auto-approval
3. Approved candidates proceed through existing generation pipeline (outline → content → QA → approve)
4. Final product approval before any publishing action
5. Any action touching external accounts, money, or public content requires operator action

---

*End of Sprint 1.7 Codex Brief. This document is the single source of truth for implementation.*
*If anything in this brief conflicts with existing code, the brief wins for Sprint 1.7 scope.*
*If Claude is unavailable, Codex implements from this document only.*
