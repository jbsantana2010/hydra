# Hermes Foundation

HYDRA is preparing agent outputs that a future Hermes coordinator can consume.
Sprint 2.6 does not install or run Hermes.

## Intended Future Role

Hermes may later become:

- coordinator
- memory layer
- long-horizon operator
- skill/refinement loop manager

## Current Boundary

HYDRA remains the system of record for:

- products
- approvals
- revenue
- budgets
- kill switch
- package files
- marketplace credentials later

Hermes-ready files are advisory outputs only. They do not trigger autonomous
execution.

## Output Contract

Agent outputs should be:

- JSON-first
- timestamped
- product-scoped
- deterministic where possible
- stored under `products/product_<id>/agent_reviews/<agent>/`

Example:

```text
products/product_43/agent_reviews/aesthetica/latest.json
```

