"""Score the checker against the author's hand labels of real lines. Writes evals/real_lines_summary.json."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rows = [json.loads(l) for l in (root / "evals/real_lines_labeled.jsonl").read_text().splitlines() if l.strip()]
bad = [r for r in rows if r["label"] != "faithful"]
s = {"lines": len(rows), "faithful": len(rows) - len(bad), "adds_words": len(bad),
     "checker_passed_all": all(r["checker"] == "pass" for r in rows),
     "false_passes": sum(r["checker"] == "pass" for r in bad), "recall_on_adds_words": f"0 of {len(bad)}" if all(r["checker"] == "pass" for r in bad) else "see rows"}
(root / "evals/real_lines_summary.json").write_text(json.dumps(s, indent=2) + "\n")
print(s)
