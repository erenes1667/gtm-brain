import csv, json, subprocess, sys, pytest
from gtm_brain.approvals import init_approvals, approve, approved_domains
from gtm_brain.export import export_sequence, NotApproved, INSTANTLY, HUBSPOT

HOOK = "plugin/hooks/require_approval.py"


def make_run(tmp_path):
    (tmp_path / "first_lines.csv").write_text(
        "domain,line,evidence,source,status,attempts,first_try_pass,problems\n"
        "a.test,Line A.,ev a,home,pass,1,True,\n"
        "b.test,Line B.,ev b,home,pass,1,True,\n"
        "c.test,Line C.,ev c,home,dropped,2,False,x\n")
    (tmp_path / "scores.csv").write_text(
        "domain,rule_score,rules_hit,llm_score,total,tier,fit,reasons\n"
        "a.test,60,x,30,90,A,strong,r\nb.test,40,x,20,60,B,ok,r\nc.test,10,x,5,15,C,weak,r\n")
    (tmp_path / "profiles.jsonl").write_text(json.dumps({"domain": "a.test", "summary": "Sells A.", "enrichment": {
        "platform": "shopify", "email_sms": ["klaviyo", "attentive"], "reviews": ["yotpo"], "helpdesk": [], "analytics": ["google_tag"],
        "careers_link": "https://a.test/careers"}}) + "\n")
    init_approvals(tmp_path, ["a.test", "b.test", "c.test"])
    return tmp_path


def test_export_blocked_without_approval(tmp_path):
    out = make_run(tmp_path)
    with pytest.raises(NotApproved):
        export_sequence(out)
    assert not (out / "export").exists()


def test_export_only_approved_rows_and_columns(tmp_path):
    out = make_run(tmp_path)
    approve(out, {"a.test", "c.test"})
    r = export_sequence(out)
    assert r["exported"] == 1 and r["skipped_no_line"] == 1  # c.test was approved but its line was dropped
    rows = list(csv.DictReader(open(out / "export/instantly.csv")))
    assert list(rows[0]) == INSTANTLY and rows[0]["website"].startswith("https://a.test/?utm_source=instantly") and rows[0]["utm_campaign"] == "gtm-brain" and rows[0]["personalization"] == "Line A."
    h = list(csv.DictReader(open(out / "export/hubspot_companies.csv")))
    assert list(h[0]) == HUBSPOT and h[0]["Description"] == "Sells A."
    assert (h[0]["gtm_platform"], h[0]["gtm_email_sms"], h[0]["gtm_helpdesk"], h[0]["gtm_careers_link"]) == ("shopify", "klaviyo;attentive", "", "https://a.test/careers")


def hook(tmp_path, payload):
    return subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True,
                          env={"GTM_OUT": str(tmp_path), "PATH": ""})


def test_hook_blocks_mcp_export_and_cli_export(tmp_path):
    out = make_run(tmp_path)
    assert hook(out, {"tool_name": "mcp__gtm-brain__export_sequence", "tool_input": {}}).returncode == 2
    cmd = {"tool_name": "Bash", "tool_input": {"command": f"uv run gtm-brain export --out {out}"}}
    assert hook(out, cmd).returncode == 2


def test_hook_allows_after_approval_and_ignores_other_tools(tmp_path):
    out = make_run(tmp_path)
    assert hook(out, {"tool_name": "Bash", "tool_input": {"command": "ls"}}).returncode == 0
    approve(out, {"a.test"})
    assert hook(out, {"tool_name": "mcp__gtm-brain__export_sequence", "tool_input": {}}).returncode == 0
    assert approved_domains(out) == {"a.test"}


def test_hubspot_dry_run_writes_payloads_and_sends_nothing(tmp_path):
    from gtm_brain.hubspot import push_companies
    out = make_run(tmp_path)
    approve(out, {"a.test"}); export_sequence(out)
    r = push_companies(out)
    assert r["mode"] == "dry-run" and r["rows"] == 1 and r["created"] == 0
    j = json.loads((out / "export/hubspot_dry_run.json").read_text())
    assert j["payloads"][0]["properties"]["domain"] == "a.test"


def test_hubspot_live_updates_existing_and_creates_new(tmp_path):
    from gtm_brain.hubspot import push_companies
    out = make_run(tmp_path)
    approve(out, {"a.test", "b.test"}); export_sequence(out)

    class R:
        def __init__(s, code=200, j=None): s.status_code, s._j = code, j or {}
        def json(s): return s._j

    class C:
        calls = []
        def post(s, url, json=None):
            s.calls.append(("POST", url))
            if url.endswith("/search"):
                return R(j={"results": [{"id": "9"}] if json["filterGroups"][0]["filters"][0]["value"] == "a.test" else []})
            return R(201)
        def patch(s, url, json=None): s.calls.append(("PATCH", url)); return R()

    r = push_companies(out, live=True, client=C())
    assert (r["updated"], r["created"], r["errors"]) == (1, 1, 0)
    assert ("PATCH", "https://api.hubapi.com/crm/v3/objects/companies/9") in C.calls


def test_hubspot_needs_export_first(tmp_path):
    from gtm_brain.hubspot import push_companies
    with pytest.raises(FileNotFoundError):
        push_companies(tmp_path)
