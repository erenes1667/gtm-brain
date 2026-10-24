"""Lifecycle tagging: new, waiting, stale, replied. Stale accounts get a follow-up draft built from
the same verified evidence, and only if the account was human approved. No LLM call, nothing is sent."""
import csv
from datetime import date
from pathlib import Path
from .approvals import approved_domains

STALE_DAYS = 30
FIELDS = ["domain", "stage", "days_since_touch", "followup_draft", "reason"]


def stage_of(last_touch, replied, today, stale_days=STALE_DAYS):
    """Return (stage, days). replied wins, no touch = new, older than stale_days = stale."""
    if str(replied).strip().lower() in {"yes", "y", "true", "1"}:
        return "replied", None
    if not str(last_touch).strip():
        return "new", None
    days = (today - date.fromisoformat(str(last_touch).strip())).days
    return ("stale" if days > stale_days else "waiting"), days


def run_lifecycle(out, accounts_csv, today=None):
    out, today = Path(out), today or date.today()
    ok = approved_domains(out)
    lines = {r["domain"]: r for r in csv.DictReader((out / "first_lines.csv").open()) if r["status"] == "pass"}
    rows = []
    for a in csv.DictReader(open(accounts_csv)):
        d = a["domain"]
        stage, days = stage_of(a.get("last_touch", ""), a.get("replied", ""), today)
        draft, reason = "", ""
        if stage == "stale":
            if d not in ok:
                reason = "not approved, no draft"
            elif d not in lines:
                reason = "no verified line, no draft"
            else:
                draft = f"Following up on my last note. {lines[d]['line']} Is this worth a short call?"
        rows.append({"domain": d, "stage": stage, "days_since_touch": "" if days is None else days, "followup_draft": draft, "reason": reason})
    with (out / "lifecycle.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS); w.writeheader(); w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r["stage"]] = counts.get(r["stage"], 0) + 1
    return {"accounts": len(rows), "stages": counts, "drafts": sum(bool(r["followup_draft"]) for r in rows)}
