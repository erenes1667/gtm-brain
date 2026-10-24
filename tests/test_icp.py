from gtm_brain.icp import load_icp, rule_score, tier_of, score_icp
from conftest import FakeLLM

ICP = load_icp("icp.yaml")
P = {"domain": "a.test", "platform": "shopify", "category": "Apparel", "price_band": "mid",
     "signals": ["klaviyo"], "products": ["socks"], "summary": "Socks."}


def test_all_rules_hit_capped_total():
    s, hits = rule_score(ICP, P)
    assert s == 60 and set(hits) == {"shopify_store", "consumer_goods", "price_mid_up", "email_stack"}


def test_no_rules_hit():
    assert rule_score(ICP, {"platform": "unknown", "category": "software", "price_band": "budget", "signals": []}) == (0, [])


def test_tiers():
    assert [tier_of(ICP, t) for t in (95, 70, 69, 50, 49)] == ["A", "A", "B", "B", "C"]


def test_score_combines_and_clamps_llm():
    llm = FakeLLM({"score": [{"score": 99, "fit": "strong", "reasons": ["a", "b"]}]})
    r = score_icp(llm, ICP, P)
    assert r["llm_score"] == 40 and r["total"] == 100 and r["tier"] == "A" and r["reasons"] == "a | b"


def test_unreadable_site_skips_llm():
    llm = FakeLLM({"score": []})
    r = score_icp(llm, ICP, {"domain": "z.test", "platform": "unknown", "category": "unknown", "summary": "", "signals": []})
    assert r["total"] == 0 and r["tier"] == "C" and llm.calls == []
