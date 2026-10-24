"""Upsert approved companies into HubSpot by domain. Dry run is the default: it writes the payloads and sends nothing.

Live mode needs HUBSPOT_TOKEN in the environment and the gtm_* company properties created in HubSpot first.
Not tested against a real portal. Offline tests use a fake client.
"""
import csv, json, os
from pathlib import Path

import httpx

API = "https://api.hubapi.com/crm/v3/objects/companies"


def _props(r):
    return {"name": r["Company name"], "domain": r["Company Domain Name"], "description": r["Description"],
            "gtm_icp_tier": r["gtm_icp_tier"], "gtm_icp_score": r["gtm_icp_score"],
            "gtm_first_line": r["gtm_first_line"], "gtm_evidence": r["gtm_evidence"],
            **{k: r.get(k, "") for k in ("gtm_platform", "gtm_email_sms", "gtm_reviews", "gtm_helpdesk", "gtm_analytics", "gtm_careers_link")}}


def push_companies(out, live=False, client=None):
    out = Path(out)
    src = out / "export" / "hubspot_companies.csv"
    if not src.exists():
        raise FileNotFoundError("run export first: no export/hubspot_companies.csv (approved rows only)")
    rows = [_props(r) for r in csv.DictReader(open(src))]
    plan, res = [], {"mode": "live" if live else "dry-run", "created": 0, "updated": 0, "errors": 0}
    if live:
        tok = os.environ.get("HUBSPOT_TOKEN")
        if not tok and client is None:
            raise RuntimeError("live mode needs HUBSPOT_TOKEN in the environment")
        client = client or httpx.Client(headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    for p in rows:
        step = {"domain": p["domain"], "properties": p}
        if live:
            q = {"filterGroups": [{"filters": [{"propertyName": "domain", "operator": "EQ", "value": p["domain"]}]}], "limit": 1}
            r = client.post(f"{API}/search", json=q)
            if r.status_code >= 400:
                res["errors"] += 1; step["action"] = f"search_failed_{r.status_code}"; plan.append(step); continue
            hit = r.json().get("results", [])
            if hit:
                r = client.patch(f"{API}/{hit[0]['id']}", json={"properties": p}); step["action"] = "update"
            else:
                r = client.post(API, json={"properties": p}); step["action"] = "create"
            if r.status_code >= 400:
                res["errors"] += 1; step["action"] += f"_failed_{r.status_code}"
            else:
                res["updated" if step["action"] == "update" else "created"] += 1
        else:
            step["action"] = "upsert_by_domain"
        plan.append(step)
    res["rows"] = len(plan)
    (out / "export" / ("hubspot_live_result.json" if live else "hubspot_dry_run.json")).write_text(
        json.dumps({"summary": res, "payloads": plan}, indent=2))
    return res
