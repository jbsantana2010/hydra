# Launch Day Checklist

- Docker is running.
- FastAPI console is live at `http://localhost:8000`.
- `curl http://localhost:8000/health` returns healthy JSON.
- Login works with `admin / change-me` or the configured `HYDRA_BASIC_USER` and `HYDRA_BASIC_PASS`.
- Mock SIGNAL scan is complete.
- A second mock SIGNAL scan skips duplicates.
- Top opportunities are visible in the console.
- One opportunity is approved by the operator.
- One product record is created from the approved opportunity.
- Product edit page opens.
- Gumroad URL is manually saved on the product after listing.
- Ruflo product prompt is generated and copied into Ruflo/Claude Code.
- Ruflo output is reviewed by the operator.
- Ruflo output is pasted into Product Artifacts in Zone B.
- Gumroad listing is manually created.
- Manual revenue event is added after a sale.
- Revenue page total and product totals look correct.
- Kill switch state is reviewed.
- Daily budget is reviewed and updated if needed.

## Manual Product Edit

1. Open `Products`.
2. Click `Edit`.
3. Update title, format, price, status, Gumroad URL, or notes.
4. Save.

Allowed statuses: `draft`, `generated`, `listed`, `live`, `paused`, `archived`.

## Manual Revenue

1. Open `Revenue`.
2. Select a product.
3. Enter amount, marketplace, currency, event type, and notes.
4. Add the event.

## Safety Settings

1. Open `Settings`.
2. Enable the kill switch to pause future spend/publish automation.
3. Disable only after the operator confirms it is safe.
4. Update `daily_budget_usd` before any future automated spending system is enabled.


## Launch Page (Sprint 1.2)

1. Open `http://localhost:8000/launch`.
2. Confirm kill-switch banner reads "disabled".
3. Confirm Approved / Products / Live counts match expectation.
4. If "Missing Gumroad URL" is non-zero, fix each product before any traffic push.
5. Top 5 opportunities and latest 5 products give a single-glance launch view.

## HackerNews Signal Collection

1. Open `http://localhost:8000/opportunities`.
2. Click "Collect HackerNews AI Signals".
3. Browser shows JSON: `{"inserted": N, "skipped": M, ...}`.
4. Hit Back; new candidates appear. They will have lower `cross_source_confirmation` (single source).
5. If kill switch is enabled, the response is HTTP 423 `{"blocked": true, ...}` and no rows are written.

## Auto-prefill on Approval

1. On the Opportunities page, click "Approve" on a candidate.
2. HYDRA creates a draft Product with prefilled title, format, price, and a structured notes block (Source / Vertical / Format / SIGNAL score / Evidence / Suggested deliverable structure / Operator notes).
3. The browser lands directly on the new product's edit page.
4. Operator edits any field, then saves.

## Artifact Export

1. On the product edit page, click "Export Artifacts to /exports".
2. Markdown files appear under `./exports/product_<id>/NNN_<type>_<slug>.md` on the host (the `exports/` folder is bind-mounted into the container).
3. If kill switch is enabled, response is HTTP 423 and no files are written.

## Product File Tracking

1. On the product edit page, click "Add File".
2. Enter a label (e.g. `main_zip`), a path (e.g. `products/my-product/my-product.zip`), an optional type and notes.
3. Save. The file record appears in the Files section of the product edit page.
4. This is path tracking only; no file is uploaded.

## What Remains Manual

- Gumroad listing creation and publishing.
- Distribution post drafting/posting in communities.
- Customer support and refunds.
- Pricing decisions.
- Any spending — the daily budget is informational until a paid-API workflow exists.
