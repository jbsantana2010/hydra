# Sprint 2.3 Handoff — Kit LLM Persistence Follow-up

**Date:** 2026-05-11  
**Status:** Complete

## Root Cause

Product 43 kit generation was using the guarded LLM adapter successfully, but `kit_doc_sections` rows were not persisting in `llm_calls`.

Two issues combined:

- The first blocker was a budget mismatch: `kit_llm_adapter.py` requested `max_cost_usd=0.30` while `HYDRA_LLM_PER_CALL_CAP_USD` was `0.20`, which blocked `kit_doc_sections` calls and forced fallback content.
- After Claude lowered the adapter budget to `0.18` and raised the env cap, LLM content generated correctly, but `app/llm.py` only `flush()`ed LLM rows. The kit route was passing a session that was no longer managed for generation, so individual `kit_doc_sections` rows did not commit.

## Fix

- `app/kit_llm_adapter.py` now commits after each `call_llm_json()` attempt, including blocked/failed logs.
- `app/kit_routes.py` now opens a live generation session for `generate_kit()` and commits it after generation.
- `.env.example` documents `HYDRA_LLM_PER_CALL_CAP_USD=0.50` with kit calls capped at `$0.18`.
- `app/kit_generator.py` writes a richer `kit_generation_report.json` with individual PDF count, master PDF status, total PDF count, and ZIP path.
- `scripts/verify_sprint23_llm_persistence.sh` verifies Product 43 output and persisted `kit_doc_sections` rows.
- `scripts/verify_sprint22.sh` was updated for Sprint 2.3's guarded adapter path instead of the old deterministic-fallback expectation.

## Verification

```bash
bash scripts/verify_sprint23.sh
LIVE=1 bash scripts/verify_sprint22.sh
bash scripts/verify_sprint23_llm_persistence.sh
```

Results:

- Sprint 2.3 verification: PASS — 42 pass, 0 fail, 0 warn.
- Sprint 2.2 live verification: PASS — 64 pass, 0 fail, 0 warn.
- LLM persistence verification: PASS — 7 pass, 0 fail, 0 warn.
- `llm_calls` now includes `kit_doc_sections|8`.

## Product 43 Status

- `kit_generation_report.json`: `llm_used=true`, `fallback_used=false`.
- 8 LLM-generated HTML documents exist.
- 8 individual root-level kit PDFs exist.
- `MASTER_Complete_Kit.pdf` exists.
- Delivery ZIP exists: `products/product_43/Real_Estate_AI_Mastery_Kit_Kit.zip`.
- No `CONTENT PENDING` or `LLM generation was not available` placeholder text found.

Note: `products/product_43/pdf/printable_pack.pdf` is the older Sprint 1.9 package PDF; Sprint 2.3 kit PDFs are root-level files under `products/product_43/`.

## Commands Run

```bash
cd /home/jb/dev/hydra
bash scripts/verify_sprint23.sh
LIVE=1 bash scripts/verify_sprint22.sh
bash scripts/verify_sprint23_llm_persistence.sh
docker compose up -d --build hydra-console
curl -s -i -u admin:change-me -X POST http://localhost:8000/kits/43/generate \
  -d 'kit_name=Real Estate AI Mastery Kit' \
  -d 'kit_tagline=The complete AI implementation system for modern agents' \
  -d 'niche=Real Estate Agents' \
  -d 'niche_context=Professional real estate agents seeking AI implementation guidance' \
  -d 'kit_edition=2026 Edition' \
  -d 'theme=real_estate'
grep -R -F 'CONTENT PENDING' products/product_43 || true
grep -R -F 'LLM generation was not available' products/product_43 || true
ls products/product_43/*.html | wc -l
ls products/product_43/pdf/*.pdf | wc -l
ls -lah products/product_43/*.zip
```

## Remaining Issues

- Some generated kit files are owned by `root` because route-based generation runs inside the container as root.
- There are two ZIPs in `products/product_43/`: the older Sprint 2.2/standalone `Real_Estate_AI_Mastery_Kit.zip` and the current route-generated `Real_Estate_AI_Mastery_Kit_Kit.zip`.
- Product 43 still needs human commercial review before listing.

## Recommended Next Step

Move toward first revenue: review the generated Product 43 PDFs and sales assets, choose the final ZIP, set a $97 Gumroad draft manually, paste the Gumroad URL back into HYDRA, and record the first listing/revenue telemetry manually.
