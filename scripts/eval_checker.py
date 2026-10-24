"""Calibrate the claim checker on labeled synthetic cases. Writes evals/checker_results.json."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gtm_brain.llm import LLM, FAST
from gtm_brain.lines import check_claims

llm = LLM("runs/ledger.jsonl", "evals/checker_cost_log.jsonl")
cases = [json.loads(x) for x in open("evals/claim_checker_cases.jsonl")]
rows = []
for c in cases:
    ok, why = check_claims(llm, c["line"], c["snippet"], "eval")
    rows.append({**c, "checker_pass": ok, "unsupported": why})
tp = sum(r["supported"] and r["checker_pass"] for r in rows)
tn = sum((not r["supported"]) and (not r["checker_pass"]) for r in rows)
fp = [r for r in rows if (not r["supported"]) and r["checker_pass"]]   # bad line let through
fn = [r for r in rows if r["supported"] and not r["checker_pass"]]     # good line rejected
res = {"model": FAST, "cases": len(rows), "accuracy": round((tp + tn) / len(rows), 3),
       "false_pass": len(fp), "false_fail": len(fn), "false_pass_cases": fp, "false_fail_cases": fn,
       "prompt_note": "CHECK_SYS in gtm_brain/lines.py"}
Path(sys.argv[1] if len(sys.argv) > 1 else "evals/checker_results.json").write_text(json.dumps(res, indent=2))
print({k: v for k, v in res.items() if not k.endswith("cases")})
