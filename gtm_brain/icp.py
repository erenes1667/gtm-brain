"""ICP scoring: YAML rules (0-60) plus an LLM judgment (0-40) with reasons."""
import yaml
from .llm import FAST, parse_json


def load_icp(path="icp.yaml"):
    return yaml.safe_load(open(path))


def _match(rule, profile):
    v = profile.get(rule["field"])
    op, want = rule["op"], rule["value"]
    if op == "eq":
        return v == want
    if op == "in":
        return v in want
    if op == "gte":
        return isinstance(v, (int, float)) and v >= want
    if op == "contains_any":
        items = v if isinstance(v, list) else [str(v or "")]
        blob = " ".join(map(str, items)).lower()
        return any(w.lower() in blob for w in want)
    raise ValueError(f"unknown op {op}")


def rule_score(icp, profile):
    hits = [r["id"] for r in icp["rules"] if _match(r, profile)]
    pts = sum(r["points"] for r in icp["rules"] if r["id"] in hits)
    return min(pts, icp.get("rule_cap", 60)), hits


def tier_of(icp, total):
    for t, floor in icp["tiers"].items():
        if total >= floor:
            return t
    return "C"


JUDGE = """You judge ICP fit for outbound. ICP: {name}. We sell: {offer}.
Given a company profile (JSON), return JSON only: {{"score": 0-{mx}, "fit": "strong"|"ok"|"weak", "reasons": [2 or 3 short strings that cite profile fields]}}.
Score high only when the profile shows an owned online store selling consumer goods at a size that plausibly runs email and SMS. Unknown data lowers the score."""


def score_icp(llm, icp, profile):
    rs, hits = rule_score(icp, profile)
    if profile.get("category") == "unknown" and not profile.get("summary"):
        ls, fit, reasons = 0, "weak", ["no readable site text"]
    else:
        sys = JUDGE.format(name=icp["name"], offer=icp["offer"], mx=icp["llm_max"])
        j = parse_json(llm.call("score", FAST, sys, str({k: profile[k] for k in
                        ("domain", "category", "products", "price_band", "platform", "signals", "summary")}),
                        max_tokens=300, domain=profile["domain"]))
        ls = max(0, min(int(j.get("score", 0)), icp["llm_max"]))
        fit, reasons = j.get("fit", "weak"), j.get("reasons", [])
    total = rs + ls
    return {"domain": profile["domain"], "rule_score": rs, "rules_hit": ";".join(hits), "llm_score": ls,
            "total": total, "tier": tier_of(icp, total), "fit": fit, "reasons": " | ".join(reasons)}
