from __future__ import annotations


def build_ruflo_product_prompt(candidate: dict) -> str:
    """Build a copyable Zone A prompt. Ruflo returns artifacts only."""
    return f"""
You are Ruflo operating as HYDRA Zone A: creative/generative swarm only.

Do not publish, spend money, call Gumroad, request credentials, or make final approval decisions.

Create a digital product plan for this approved opportunity:

Topic: {candidate.get("topic")}
Vertical: {candidate.get("vertical")}
Format: {candidate.get("production_format")}
Evidence: {candidate.get("evidence")}
SIGNAL score: {candidate.get("score")}

Return:
1. Product promise
2. Target buyer
3. Table of contents or asset list
4. Draft sections/assets
5. QA critique
6. Production checklist
""".strip()


def build_ruflo_listing_prompt(product: dict) -> str:
    """Build Gumroad listing copy prompt without marketplace access."""
    return f"""
You are Ruflo operating as HYDRA Zone A: creative copy and critique only.

Do not publish, spend money, call Gumroad, request credentials, or make final approval decisions.

Draft listing copy for this product:

Title: {product.get("title")}
Format: {product.get("production_format")}
Price: {product.get("price")}
Notes: {product.get("notes")}

Return:
1. Short title variants
2. Gumroad description
3. Bullet benefits
4. Included files/assets
5. FAQ
6. Launch post drafts
7. Risks or overclaims to remove
""".strip()
