from gtm_brain.deliverability import check_domain


def fake(records):
    return lambda name: records.get(name, [])


def test_clean_domain_has_no_issues():
    r = check_domain("m.test", fake({"m.test": ["v=spf1 include:x.test -all"], "_dmarc.m.test": ["v=DMARC1; p=reject"],
                                     "google._domainkey.m.test": ["v=DKIM1; k=rsa; p=ABC"]}))
    assert r["issues"] == [] and r["dkim_selectors_found"] == ["google"] and r["dmarc_policy"] == "reject"


def test_missing_records_are_reported():
    r = check_domain("m.test", fake({"m.test": ["v=spf1 +all"], "_dmarc.m.test": ["v=DMARC1; p=none"]}))
    assert set(r["issues"]) == {"SPF allows any sender", "DMARC policy is none (monitor only)",
                                "no DKIM key found on the common selectors (your sender may use another)"}
    assert "no SPF record" in check_domain("n.test", fake({}))["issues"]

