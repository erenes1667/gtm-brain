"""Sequence export for Instantly and HubSpot. Approved rows only."""
import csv, json
from pathlib import Path
from .approvals import approved_domains

INSTANTLY = ["email", "first_name", "last_name", "company_name", "website", "personalization", "icp_tier", "icp_score", "utm_campaign"]
HUBSPOT = ["Company name", "Company Domain Name", "Description", "gtm_icp_tier", "gtm_icp_score", "gtm_first_line", "gtm_evidence",
           "gtm_platform", "gtm_email_sms", "gtm_reviews", "gtm_helpdesk", "gtm_analytics", "gtm_careers_link"]


class NotApproved(PermissionError):
    pass


def _rows(path):
    return list(csv.DictReader(open(path))) if Path(path).exists() else []


def name_of(domain):
    return domain.split(".")[0].replace("-", " ").title()


def export_sequence(out, campaign="gtm-brain"):
    out = Path(out)
    ok = approved_domains(out)
    if not ok:
        raise NotApproved("no approved rows in approvals.csv, export blocked")
    lines = {r["domain"]: r for r in _rows(out / "first_lines.csv") if r["status"] == "pass"}
    scores = {r["domain"]: r for r in _rows(out / "scores.csv")}
    pj = out / "profiles.jsonl"
    profiles = {j["domain"]: j for j in map(json.loads, pj.read_text().splitlines())} if pj.exists() else {}
    ex = out / "export"
    ex.mkdir(exist_ok=True)
    keep = [d for d in ok if d in lines]
    with open(ex / "instantly.csv", "w", newline="") as fi, open(ex / "hubspot_companies.csv", "w", newline="") as fh:
        wi, wh = csv.DictWriter(fi, INSTANTLY), csv.DictWriter(fh, HUBSPOT)
        wi.writeheader(); wh.writeheader()
        for d in sorted(keep):
            s, l = scores[d], lines[d]
            wi.writerow({"email": "", "first_name": "", "last_name": "", "company_name": name_of(d), "website": f"https://{d}/?utm_source=instantly&utm_medium=email&utm_campaign={campaign}",
                         "personalization": l["line"], "icp_tier": s["tier"], "icp_score": s["total"],
                         "utm_campaign": campaign})
            en = profiles.get(d, {}).get("enrichment") or {}
            j = lambda k: ";".join(en.get(k) or [])
            wh.writerow({"Company name": name_of(d), "Company Domain Name": d,
                         "Description": profiles.get(d, {}).get("summary", ""), "gtm_icp_tier": s["tier"],
                         "gtm_icp_score": s["total"], "gtm_first_line": l["line"], "gtm_evidence": l["evidence"],
                         "gtm_platform": en.get("platform", ""), "gtm_email_sms": j("email_sms"), "gtm_reviews": j("reviews"),
                         "gtm_helpdesk": j("helpdesk"), "gtm_analytics": j("analytics"), "gtm_careers_link": en.get("careers_link") or ""})
    return {"exported": len(keep), "approved": len(ok), "skipped_no_line": len(ok) - len(keep), "dir": str(ex)}
