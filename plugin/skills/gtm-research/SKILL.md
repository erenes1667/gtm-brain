---
name: gtm-research
description: Fetch and profile company websites for outbound research. Use for a list of company domains that need category, price band and platform signals before scoring.
---
# gtm-research

Use the MCP tools in this order. Do not fetch pages by any other route.

1. `fetch_site(domain)`: cached, robots-aware. Reads the homepage and one about or collections page only. If `error` is `blocked_by_robots`, stop for that domain and say so.
2. `extract_company_profile(domain)`: Haiku reads the text and returns category, products, price band, tech hints. Platform signals (Shopify and others) come from HTML rules, not the model.
3. For a whole CSV, run `uv run gtm-brain run <csv> --out <dir>` instead of looping tools.

Rules: company level data only. No people, no emails, no scraping beyond two pages per domain. A missing field stays `unknown`. Never fill it with a guess.
