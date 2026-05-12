# HYDRA Agent Standards

This folder defines local agent standards that HYDRA can use without adding an
external runtime. Agents here are specifications plus deterministic support code;
HYDRA remains the system of record.

Current agents:

- `AESTHETICA` - visual and commercial design critic for marketplace assets.

Future Hermes compatibility:

- Agent outputs should be JSON-first.
- Agent reviews should be written under `products/product_<id>/agent_reviews/`.
- Agents may critique, score, and recommend fixes.
- Agents must not publish, spend money, scrape, or alter revenue state.

