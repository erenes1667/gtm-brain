"""Company profile: deterministic signals plus a Haiku read of the page text."""
from .llm import FAST, parse_json

SYSTEM = """You read public website text for one DTC e-commerce company and return JSON only.
Keys: category (short phrase, e.g. "apparel", "home goods"), products (up to 5 short strings),
price_band ("budget"|"mid"|"premium"|"unknown", judged only from prices or wording in the text),
tech_hints (list of strings, only if the text itself names a tool), summary (one sentence, max 25 words).
Use only the text given. If unclear, use "unknown" or an empty list. No guessing."""


def site_text(site):
    return "\n\n".join(f"[{p['kind']}] {p['text']}" for p in site["pages"])


def extract_company_profile(llm, site):
    base = {"domain": site["domain"], "platform": site["platform"], "signals": site["signals"],
            "pages": [p["url"] for p in site["pages"]], "error": site.get("error"), "enrichment": site.get("enrichment")}
    if not site["pages"]:
        return {**base, "category": "unknown", "products": [], "price_band": "unknown",
                "tech_hints": [], "summary": ""}
    raw = llm.call("profile", FAST, SYSTEM, site_text(site), max_tokens=500, domain=site["domain"])
    j = parse_json(raw)
    return {**base, "category": j.get("category", "unknown"), "products": j.get("products", [])[:5],
            "price_band": j.get("price_band", "unknown"), "tech_hints": j.get("tech_hints", []),
            "summary": j.get("summary", "")}
