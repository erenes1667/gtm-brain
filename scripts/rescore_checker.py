"""Re-run the claim checker (current prompt) on the 30 hand-labeled real lines and the 24 synthetic cases.
Writes evals/real_lines_rescored.json. Live: needs the personal key in env."""
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from gtm_brain.llm import LLM, load_env
from gtm_brain.lines import check_claims

load_env()
llm = LLM(str(root / "runs/ledger.jsonl"), str(root / "evals/rescore_cost_log.jsonl"))
rows = [json.loads(l) for l in (root / "evals/real_lines_labeled.jsonl").read_text().splitlines() if l.strip()]
out = []
for r in rows:
    ok, why = check_claims(llm, r["line"], r["evidence"], r["domain"])
    out.append({"domain": r["domain"], "label": r["label"], "old": r["checker"], "new": "pass" if ok else "fail", "unsupported": why})
bad = [o for o in out if o["label"] != "faithful"]; good = [o for o in out if o["label"] == "faithful"]
cases = [json.loads(x) for x in (root / "evals/claim_checker_cases.jsonl").read_text().splitlines() if x.strip()]
cres = [(c["supported"], check_claims(llm, c["line"], c["snippet"], "eval")[0]) for c in cases]
s = {"prompt": "CHECK_SYS in gtm_brain/lines.py (tightened 2026-10-24)",
     "real_lines": len(out), "padded_caught": f"{sum(o['new']=='fail' for o in bad)} of {len(bad)}",
     "faithful_wrongly_failed": f"{sum(o['new']=='fail' for o in good)} of {len(good)}",
     "synthetic_cases": len(cases), "synthetic_false_pass": sum((not a) and b for a, b in cres),
     "synthetic_false_fail": sum(a and (not b) for a, b in cres), "rows": out}
(root / "evals/real_lines_rescored.json").write_text(json.dumps(s, indent=2) + "\n")
print({k: v for k, v in s.items() if k != "rows"})
