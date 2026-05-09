# Verification Results

Append-only summary of what was verified, with timestamps. One entry per sprint completion (or per major mid-sprint validation).

---

## Sprint 1.2 — 2026-05-08

| Check | Result |
|---|---|
| `curl /health` | 200 `{"status":"healthy"}` |
| Mock SIGNAL scan idempotent | inserted 0, skipped 12 on second run |
| HN collect (query=`AI agents`) | fetched 12, scored 12, inserted 12 |
| Approve auto-prefill | 303 → `/products/<new_id>/edit` with prefilled title/format/price/notes |
| Approve idempotency | re-approving same candidate returns existing product, no duplicate |
| Add file record | 303; row visible on edit page |
| Add artifact | 303; row visible on edit page |
| Artifact export | wrote `001_<type>_<slug>.md` under `./exports/product_<id>/` on the host |
| Kill switch blocks HN collect | HTTP 423 + `{"blocked":true,...}` |
| Kill switch blocks artifact export | HTTP 423 + `{"blocked":true,...}` |
| URL warning: `live` + empty | warn banner "Live status set without a Gumroad URL." |
| URL warning: malformed | warn banner "must start with http:// or https://" |
| URL warning: healthy | good banner "Launch URL ready." |
| Launch dashboard renders | 200 with all metric cards present |
