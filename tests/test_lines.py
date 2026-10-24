from gtm_brain.lines import banned_hits, evidence_in_text, make_line
from conftest import FakeLLM

GOOD = {"line": "Acme cuts every sock pattern by hand.", "evidence": "we cut every sock pattern by hand", "source": "second"}


def test_banned_phrases_dashes_length():
    assert banned_hits("I hope this finds you well") == ["i hope this finds you well"]
    assert "dash" in banned_hits("Great socks — really")
    assert banned_hits("word " * 31).pop().startswith("over_")
    assert banned_hits("Acme makes socks.") == []


def test_evidence_must_be_verbatim(site):
    assert evidence_in_text("Free shipping over $50.", site)
    assert evidence_in_text("WE CUT  every sock pattern by hand", site)
    assert not evidence_in_text("Free shipping over $100.", site)
    assert not evidence_in_text("short", site)


def test_pass_first_try(site):
    llm = FakeLLM({"line": [GOOD], "check": [{"pass": True, "unsupported_claims": []}]})
    r = make_line(llm, site)
    assert r["status"] == "pass" and r["first_try_pass"] and r["attempts"] == 1


def test_rewrite_after_checker_fail(site):
    bad = {**GOOD, "line": "Acme cuts every sock pattern by hand since 1999."}
    llm = FakeLLM({"line": [bad, GOOD], "check": [{"pass": False, "unsupported_claims": ["since 1999"]}, {"pass": True}]})
    r = make_line(llm, site)
    assert r["status"] == "pass" and r["attempts"] == 2 and r["first_try_pass"] is False


def test_invented_evidence_never_reaches_checker(site):
    fake = {"line": "Acme ships free.", "evidence": "Acme ships free worldwide always", "source": "home"}
    llm = FakeLLM({"line": [fake, fake], "check": []})
    r = make_line(llm, site)
    assert r["status"] == "dropped" and not any(c[0] == "check" for c in llm.calls)


def test_banned_line_dropped_after_retry(site):
    b = {**GOOD, "line": "Acme is a game-changer in socks."}
    llm = FakeLLM({"line": [b, b], "check": []})
    assert make_line(llm, site)["status"] == "dropped"


def test_unparseable_checker_fails_closed(site):
    llm = FakeLLM({"line": [GOOD, GOOD], "check": ["I think this is fine, because...", "still prose"]})
    r = make_line(llm, site)
    assert r["status"] == "dropped" and "checker_unparseable" in r["problems"]
