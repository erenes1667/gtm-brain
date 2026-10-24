import csv
from datetime import date
from gtm_brain.lifecycle import stage_of, run_lifecycle
from gtm_brain.approvals import approve
from tests.test_approval_export import make_run

T = date(2026, 10, 24)


def test_stage_rules():
    assert stage_of("", "", T) == ("new", None)
    assert stage_of("2026-10-20", "", T) == ("waiting", 4)
    assert stage_of("2026-08-01", "", T) == ("stale", 84)
    assert stage_of("2026-08-01", "yes", T) == ("replied", None)
    assert stage_of("2026-09-24", "", T)[0] == "waiting"  # exactly 30 days is not stale


def test_draft_needs_approval_and_verified_line(tmp_path):
    out = make_run(tmp_path)
    approve(out, {"a.test"})  # b.test passes the line check but is not approved; c.test line was dropped
    acc = tmp_path / "acc.csv"
    acc.write_text("domain,last_touch,replied\na.test,2026-08-01,\nb.test,2026-08-01,\nc.test,2026-08-01,\n")
    res = run_lifecycle(out, acc, T)
    rows = {r["domain"]: r for r in csv.DictReader((out / "lifecycle.csv").open())}
    assert res["drafts"] == 1 and "Line A." in rows["a.test"]["followup_draft"]
    assert rows["b.test"]["followup_draft"] == "" and "not approved" in rows["b.test"]["reason"]
    assert rows["c.test"]["followup_draft"] == ""
