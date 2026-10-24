"""Human approval gate. approvals.csv is the only thing that unlocks export."""
import csv
from pathlib import Path

YES = {"yes", "y", "true", "1", "approved"}
FIELDS = ["domain", "approved", "note"]


def init_approvals(out, domains):
    p = Path(out) / "approvals.csv"
    if p.exists():
        return p
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        for d in domains:
            w.writerow({"domain": d, "approved": "", "note": ""})
    return p


def approved_domains(out):
    p = Path(out) / "approvals.csv"
    if not p.exists():
        return set()
    return {r["domain"] for r in csv.DictReader(p.open()) if r.get("approved", "").strip().lower() in YES}


def approve(out, domains, note="approved"):
    p = Path(out) / "approvals.csv"
    rows = list(csv.DictReader(p.open()))
    for r in rows:
        if r["domain"] in domains:
            r["approved"], r["note"] = "yes", note
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    return len([r for r in rows if r["approved"] == "yes"])
