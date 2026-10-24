"""Orchestrates fetch, profile, score, line, check. Writes run artifacts."""
import csv, json, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .approvals import init_approvals
from .fetch import Fetcher
from .icp import load_icp, score_icp
from .lines import make_line
from .llm import BudgetExceeded
from .profile import extract_company_profile

SCORE_FIELDS = ["domain", "rule_score", "rules_hit", "llm_score", "total", "tier", "fit", "reasons"]
LINE_FIELDS = ["domain", "line", "evidence", "source", "status", "attempts", "first_try_pass", "first_problems", "problems"]


def read_domains(path):
    rows = list(csv.DictReader(open(path)))
    return [r["domain"].strip().lower() for r in rows if r.get("domain", "").strip()]


def process(domain, fetcher, llm, icp):
    t0 = time.time()
    site = fetcher.fetch_site(domain)
    profile = extract_company_profile(llm, site)
    score = score_icp(llm, icp, profile)
    line = None
    if score["tier"] in icp["write_lines_for"] and site["pages"]:
        line = make_line(llm, site)
        line["domain"] = domain
    return {"profile": profile, "score": score, "line": line, "seconds": round(time.time() - t0, 2)}


def safe_process(domain, fetcher, llm, icp):
    """One bad account must not kill the run. The error is recorded in the profile."""
    try:
        return process(domain, fetcher, llm, icp)
    except BudgetExceeded:
        raise
    except Exception as e:
        profile = {"domain": domain, "platform": "unknown", "signals": [], "pages": [], "category": "unknown",
                   "products": [], "price_band": "unknown", "tech_hints": [], "summary": "",
                   "error": f"pipeline_error:{type(e).__name__}: {str(e)[:120]}", "enrichment": None}
        score = {"domain": domain, "rule_score": 0, "rules_hit": "", "llm_score": 0, "total": 0, "tier": "C",
                 "fit": "weak", "reasons": profile["error"]}
        return {"profile": profile, "score": score, "line": None, "seconds": 0}


def run(domains_csv, out, llm, icp_path="icp.yaml", fetcher=None, workers=4):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    icp, fetcher = load_icp(icp_path), fetcher or Fetcher()
    domains = read_domains(domains_csv)
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(lambda d: safe_process(d, fetcher, llm, icp), domains))
    (out / "profiles.jsonl").write_text("".join(json.dumps(r["profile"]) + "\n" for r in results))
    for name, fields, rows in (("scores.csv", SCORE_FIELDS, [r["score"] for r in results]),
                               ("first_lines.csv", LINE_FIELDS, [r["line"] for r in results if r["line"]])):
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    init_approvals(out, [r["line"]["domain"] for r in results if r["line"] and r["line"]["status"] == "pass"])
    m = metrics(results, out)
    m["wall_seconds"] = round(time.time() - t_start, 1)
    m["workers"] = workers
    (out / "metrics.json").write_text(json.dumps(m, indent=2))
    return m


def metrics(results, out):
    lines = [r["line"] for r in results if r["line"]]
    first = sum(1 for l in lines if l["first_try_pass"])
    final = sum(1 for l in lines if l["status"] == "pass")
    calls = [json.loads(x) for x in (Path(out) / "cost_log.jsonl").read_text().splitlines()] if (Path(out) / "cost_log.jsonl").exists() else []
    by_model = defaultdict(float)
    for c in calls:
        by_model[c["model"]] += c["usd"]
    usd = sum(c["usd"] for c in calls)
    n = len(results)
    return {
        "accounts": n,
        "fetched_ok": sum(1 for r in results if r["profile"]["pages"]),
        "fetch_errors": {r["profile"]["domain"]: r["profile"]["error"] for r in results if r["profile"]["error"]},
        "tiers": {t: sum(1 for r in results if r["score"]["tier"] == t) for t in "ABC"},
        "lines_attempted": len(lines),
        "first_try_pass": first,
        "first_try_pass_rate": round(first / len(lines), 3) if lines else None,
        "final_pass": final,
        "dropped": len(lines) - final,
        "llm_calls": len(calls),
        "cost_usd_total": round(usd, 4),
        "cost_usd_by_model": {k: round(v, 4) for k, v in by_model.items()},
        "cost_usd_per_account": round(usd / n, 4) if n else None,
        "cost_usd_per_approved_line": round(usd / final, 4) if final else None,
        "avg_seconds_per_account": round(sum(r["seconds"] for r in results) / n, 2) if n else None,
    }


def cost_report(out):
    p = Path(out) / "cost_log.jsonl"
    calls = [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
    agg = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0})
    for c in calls:
        a = agg[f"{c['stage']}|{c['model']}"]
        a["calls"] += 1; a["input_tokens"] += c["input_tokens"]; a["output_tokens"] += c["output_tokens"]; a["usd"] = round(a["usd"] + c["usd"], 6)
    return {"by_stage_model": dict(agg), "total_usd": round(sum(c["usd"] for c in calls), 4)}
