# Build vs buy

Build numbers come from files in this repo. Clay numbers come from clay.com/pricing, read on 2026-10-24. The page is inconsistent: the plan header says Launch $167/mo and Growth $446/mo, the FAQ says $185/mo and $495/mo. Treat vendor numbers as unverified list prices.

| Stage | Build here, per 1,000 accounts | Buy (Clay list price) |
|---|---|---|
| Fetch two public pages | Free. Cost is engineering time and a block rate: 6 of 25 live, 4 of 19 held-out failed | Clay runs enrichment and scraping as billed actions. "Actions start at less than $0.01 each" |
| Haiku stages (profile, score, claim check) | $0.1261 per 25 accounts live, about $5.04 | Not a like-for-like product. Clay AI columns use actions or credits, price per row not stated on the page |
| Opening line (Sonnet) | $0.2853 per 25 accounts live, about $11.41 | Same as above |
| Claim check and gates | Included in the totals above. No vendor equivalent was found | None checked |
| Email or contact data | Not built. Export has an empty email column | "Data credits start at $0.05 each". Launch plan: 3,000 credits and 15,000 actions a month |
| Total, LLM cost | $16.50 live ($0.4114 / 25), $17.46 held-out ($0.3318 / 19). Extrapolations | Launch plan $167/mo (or $185/mo per the FAQ) covers 15,000 actions |

Assumed, not measured: the per-1,000 figures scale linearly from 25 and 19 accounts. The rates in `pricing.yaml` are assumed list prices. Clay's per-row cost for an AI step was not on the page, so no like-for-like total is claimed.

Conclusion: buy contact data and waterfalls. Build the evidence gate, the checker, the approval step and the cost log, because those set quality and risk and no vendor was found that offers them.
