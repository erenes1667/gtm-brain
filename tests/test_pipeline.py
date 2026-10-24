import csv, json
from gtm_brain import pipeline
from gtm_brain.fetch import Fetcher
from conftest import FakeLLM


class Stub(Fetcher):
    def __init__(self, sites): self.sites = sites
    def fetch_site(self, d): return self.sites[d]


def test_end_to_end_offline(tmp_path, site):
    dead = {"domain": "dead.test", "pages": [], "signals": [], "platform": "unknown", "error": "http_404"}
    (tmp_path / "d.csv").write_text("domain\nacme.test\ndead.test\n")
    llm = FakeLLM({
        "profile": [{"category": "apparel", "products": ["socks"], "price_band": "mid", "tech_hints": [], "summary": "Wool socks."}],
        "score": [{"score": 35, "fit": "strong", "reasons": ["shopify"]}],
        "line": [{"line": "Acme cuts every sock pattern by hand.", "evidence": "we cut every sock pattern by hand", "source": "second"}],
        "check": [{"pass": True, "unsupported_claims": []}]})
    m = pipeline.run(tmp_path / "d.csv", tmp_path / "out", llm, fetcher=Stub({"acme.test": site, "dead.test": dead}), workers=1)
    assert m["accounts"] == 2 and m["fetched_ok"] == 1 and m["final_pass"] == 1 and m["first_try_pass_rate"] == 1.0
    assert m["tiers"] == {"A": 1, "B": 0, "C": 1}
    assert [r["domain"] for r in csv.DictReader(open(tmp_path / "out/approvals.csv"))] == ["acme.test"]


def test_one_bad_account_does_not_kill_run(tmp_path, site):
    (tmp_path / "d.csv").write_text("domain\nacme.test\n")
    llm = FakeLLM({"profile": ["not json at all"]})
    m = pipeline.run(tmp_path / "d.csv", tmp_path / "out", llm, fetcher=Stub({"acme.test": site}), workers=1)
    assert m["accounts"] == 1 and m["tiers"]["C"] == 1 and "acme.test" in m["fetch_errors"]


def test_mcp_server_exposes_seven_tools():
    import asyncio
    from gtm_brain.server import mcp
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"fetch_site", "extract_company_profile", "score_icp", "write_first_line", "export_sequence", "cost_report", "check_sending_domain"}


def test_budget_cap_blocks_call(tmp_path):
    import json, pytest
    from gtm_brain.llm import LLM, BudgetExceeded
    led = tmp_path / "l.jsonl"; led.write_text(json.dumps({"usd": 6.5}) + "\n")
    with pytest.raises(BudgetExceeded):
        LLM(led, budget=6, client=object()).call("x", "claude-haiku-5-5", "s", "u")
