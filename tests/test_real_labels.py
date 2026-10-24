import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_real_label_summary_matches_rows():
    rows = [json.loads(l) for l in (ROOT / "evals/real_lines_labeled.jsonl").read_text().splitlines() if l.strip()]
    s = json.loads((ROOT / "evals/real_lines_summary.json").read_text())
    bad = [r for r in rows if r["label"] != "faithful"]
    assert s["lines"] == len(rows) == 30 and s["adds_words"] == len(bad) == 6 and s["false_passes"] == 6


def test_rescored_summary_matches_rows():
    s = json.loads((ROOT / "evals/real_lines_rescored.json").read_text())
    bad = [r for r in s["rows"] if r["label"] != "faithful"]
    good = [r for r in s["rows"] if r["label"] == "faithful"]
    assert s["padded_caught"] == f"{sum(r['new'] == 'fail' for r in bad)} of {len(bad)}"
    assert s["faithful_wrongly_failed"] == f"{sum(r['new'] == 'fail' for r in good)} of {len(good)}"
