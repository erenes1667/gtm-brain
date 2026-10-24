from gtm_brain.llm import parse_json, cost_usd
from gtm_brain.fetch import detect_signals, platform_of, pick_second_page, page_text, Fetcher


def test_parse_json_fenced_and_chatty():
    assert parse_json('Sure!\n```json\n{"a": {"b": "x}"}}\n```\nbye') == {"a": {"b": "x}"}}


def test_parse_json_missing():
    import pytest
    with pytest.raises(ValueError):
        parse_json("no json here")


def test_cost_math():
    p = {"m": {"input": 1.0, "output": 5.0}}
    assert cost_usd("m", 1_000_000, 200_000, p) == 2.0


def test_signals_and_platform():
    html = '<script src="https://cdn.shopify.com/s/x.js"></script><script src="//static.klaviyo.com/a.js"></script>'
    s = detect_signals(html)
    assert s == ["klaviyo", "shopify"] and platform_of(s) == "shopify"
    assert platform_of([]) == "unknown"


def test_pick_second_page_prefers_about_same_host():
    html = '<a href="/collections/all">Shop</a><a href="/pages/about-us">About</a><a href="https://other.com/about">x</a><a href="/cart">Cart</a>'
    assert pick_second_page(html, "https://acme.test/") == "https://acme.test/pages/about-us"


def test_page_text_strips_scripts():
    assert page_text("<body><script>x=1</script><p>Hello   world</p></body>") == "Hello world"


class Resp:
    def __init__(self, code, text): self.status_code, self.text = code, text


class FakeHttp:
    def __init__(self, routes): self.routes, self.hits = routes, []
    def get(self, url):
        self.hits.append(url)
        return self.routes.get(url, Resp(404, ""))


def test_robots_disallow_blocks_fetch(tmp_path):
    http = FakeHttp({"https://x.test/robots.txt": Resp(200, "User-agent: *\nDisallow: /"),
                     "https://x.test/": Resp(200, "<p>hi</p>")})
    out = Fetcher(tmp_path, http, delay=0).fetch_site("x.test")
    assert out["error"] == "blocked_by_robots" and "https://x.test/" not in http.hits


def test_fetch_caches_and_limits_pages(tmp_path):
    home = '<p>Shop</p><a href="/pages/about">About</a><a href="/collections/a">C</a>'
    http = FakeHttp({"https://x.test/": Resp(200, home), "https://x.test/pages/about": Resp(200, "<p>story</p>"),
                     "https://x.test/robots.txt": Resp(404, "")})
    f = Fetcher(tmp_path, http, delay=0)
    a = f.fetch_site("x.test")
    n = len(http.hits)
    b = f.fetch_site("x.test")
    assert [p["kind"] for p in a["pages"]] == ["home", "second"] and b["cached"] and len(http.hits) == n
    assert sum(1 for h in http.hits if "robots" not in h) == 2


def test_redirect_to_other_host_rechecks_robots(tmp_path):
    class RR(Resp):
        def __init__(self, code, text, url): super().__init__(code, text); self.url = url
    http = FakeHttp({"https://x.test/robots.txt": RR(404, "", "https://x.test/robots.txt"),
                     "https://x.test/": RR(200, "<p>hi</p>", "https://other.test/"),
                     "https://other.test/robots.txt": RR(200, "User-agent: *\nDisallow: /", "https://other.test/robots.txt")})
    assert Fetcher(tmp_path, http, delay=0).fetch_site("x.test")["error"] == "blocked_by_robots_after_redirect"


def test_robots_5xx_counts_as_blocked(tmp_path):
    http = FakeHttp({"https://x.test/robots.txt": Resp(503, ""), "https://x.test/": Resp(200, "<p>hi</p>")})
    assert Fetcher(tmp_path, http, delay=0).fetch_site("x.test")["error"] == "blocked_by_robots"


def test_second_page_redirect_to_other_host_rechecks_robots(tmp_path):
    class RR(Resp):
        def __init__(self, code, text, url): super().__init__(code, text); self.url = url
    home = '<a href="/pages/about">About</a>'
    http = FakeHttp({"https://x.test/robots.txt": RR(404, "", "https://x.test/robots.txt"),
                     "https://x.test/": RR(200, home, "https://x.test/"),
                     "https://x.test/pages/about": RR(200, "<p>moved</p>", "https://other.test/about"),
                     "https://other.test/robots.txt": RR(200, "User-agent: *\nDisallow: /", "https://other.test/robots.txt")})
    out = Fetcher(tmp_path, http, delay=0).fetch_site("x.test")
    assert [p["kind"] for p in out["pages"]] == ["home"]
