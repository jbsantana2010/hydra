# Ruflo Boundary

Ruflo is Zone A.

Zone A is the creative/generative swarm. Ruflo can generate:

- Opportunity summaries
- Product outlines
- Draft product sections
- Listing copy
- Distribution drafts
- QA critiques

Ruflo must never:

- Hold Gumroad credentials
- Publish marketplace listings
- Spend money
- Own marketplace API access
- Make final approval decisions
- Modify product status, revenue, budget, or kill switch state

FastAPI/Postgres/Redis is Zone B.

Zone B owns:

- Approvals
- Product records
- Gumroad credentials
- Money and state
- Budget caps
- Kill switch
- Revenue ledger
- Marketplace publishing

Hard rule: Ruflo outputs proposals and artifacts only. Zone B stores, approves, publishes, and tracks.

## Artifact Import

Ruflo output can be pasted manually into HYDRA:

1. Open `Products`.
2. Select `Edit` for the relevant product.
3. Select `Add Artifact`.
4. Choose one of: `outline`, `product_content`, `listing_copy`, `qa_review`, `distribution_post`.
5. Paste the generated content.
6. Store it in Zone B.

This keeps Ruflo creative output available to the operator without giving Ruflo credentials, publishing authority, budget control, or revenue access.
