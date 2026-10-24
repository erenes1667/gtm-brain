from pathlib import Path
from gtm_brain.enrich import enrich_html, merge
from gtm_brain.fetch import Fetcher
from test_parsing_fetch import FakeHttp, Resp

FX = Path(__file__).parent / "fixtures"
read = lambda n: (FX / n).read_text()


def test_full_store_detects_every_group():
    e = enrich_html(read("store_full.html"), "https://acme.test/")
    assert e == {"platform": "shopify", "email_sms": ["attentive", "klaviyo"], "reviews": ["yotpo"], "helpdesk": ["gorgias"],
                 "analytics": ["google_tag", "meta_pixel"], "careers_link": "https://acme.test/pages/careers"}


def test_visible_text_is_not_a_detection_and_job_board_counts_as_careers():
    e = enrich_html(read("store_plain.html"), "https://plain.test/")
    assert e["platform"] == "unknown" and e["email_sms"] == [] and e["helpdesk"] == []
    assert e["careers_link"] == "https://boards.greenhouse.io/plainco"


def test_bigcommerce_zendesk_judgeme_omnisend_and_no_careers():
    e = enrich_html(read("store_bigc.html"), "https://b.test/")
    assert (e["platform"], e["helpdesk"], e["reviews"], e["email_sms"], e["careers_link"]) == \
        ("bigcommerce", ["zendesk"], ["judge.me"], ["omnisend"], None)


def test_merge_unions_and_keeps_first_platform():
    a = enrich_html(read("store_full.html"), "https://acme.test/")
    b = enrich_html(read("store_bigc.html"), "https://acme.test/")
    m = merge(a, b)
    assert m["platform"] == "shopify" and "zendesk" in m["helpdesk"] and "gorgias" in m["helpdesk"]
    assert merge(None, b) == b


def test_fetch_stores_enrichment_with_no_extra_requests(tmp_path):
    http = FakeHttp({"https://x.test/": Resp(200, read("store_full.html")), "https://x.test/robots.txt": Resp(404, "")})
    out = Fetcher(tmp_path, http, delay=0).fetch_site("x.test")
    assert out["enrichment"]["platform"] == "shopify" and out["enrichment"]["careers_link"].endswith("/pages/careers")
    assert http.hits.count("https://x.test/") == 1


def test_malformed_href_with_embedded_url_is_cleaned():
    html = '<a href="https://b.test/en-frhttps:/www.example.com/company/b/jobs/">Careers</a>'
    assert enrich_html(html, "https://b.test/")["careers_link"] == "https://www.example.com/company/b/jobs/"
