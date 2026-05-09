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


## Sprint 1.3 — Launch Learning v1

### Recording where a launch post went

1. After publishing the launch post manually (Twitter, Reddit, HN, blog, Discord, etc.), open the product's edit page in HYDRA.
2. Find the `distribution_post` artifact.
3. In the form below it, paste the URL of the post and a short `channel_tag` (`twitter`, `reddit`, `hn`, `blog`, `discord`, `newsletter`).
4. Click "Mark Published". The artifact will now show a green banner with the URL, channel, and publish timestamp.
5. The launch dashboard's "Live without distribution" metric will drop by one.

### Logging a sale with attribution

1. Open `Revenue`.
2. Pick the product, fill in `amount` and `currency`.
3. Set `channel_tag` to match the channel that drove the sale (`twitter`, `reddit`, etc.).
4. Paste the URL of the post into `Source attribution`.
5. Optionally add notes.
6. Add Revenue. The launch dashboard's "Revenue by channel" rollup updates immediately.

### Approving a new candidate (Sprint 1.3 prefill)

1. On Opportunities, click Approve.
2. The new product's edit page now shows a clean title like `"Topic name — Cheat Sheet"` (no awkward `Pdf:` prefix).
3. HN candidates are routed to a more specific `vertical` and `production_format` pair via the keyword classifier (`AI coding tools / cheat sheet PDF` for agent-related stories, etc.).

### Exporting artifacts also tracks the files

1. On the product edit page, click "Export Artifacts to /exports".
2. Markdown files appear under `./exports/product_<id>/` AND `product_files` rows are auto-registered for each export.
3. The Files section on the edit page now shows them; running export again does not duplicate.
