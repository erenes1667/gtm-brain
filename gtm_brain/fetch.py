"""Robots-aware, cached fetch of a homepage plus one about/collections page."""
import hashlib, json, re, time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from .enrich import enrich_html, merge

UA = "gtm-brain-demo/0.1 (portfolio research bot; company homepages only; honors robots.txt)"
MAX_CHARS = 6000

# Platform and tech signals read from public HTML. Rules, no LLM.
SIGNALS = {
    "shopify": [r"cdn\.shopify\.com", r"Shopify\.theme", r"/cdn/shop/"],
    "woocommerce": [r"woocommerce", r"wp-content/plugins/woocommerce"],
    "bigcommerce": [r"cdn\d*\.bigcommerce\.com", r"bigcommerce"],
    "magento": [r"Magento", r"/static/version\d+/"],
    "klaviyo": [r"klaviyo\.com", r"static\.klaviyo"],
    "attentive": [r"attn\.tv", r"attentivemobile"],
    "yotpo": [r"yotpo"],
    "gorgias": [r"gorgias"],
    "google_analytics": [r"googletagmanager\.com", r"google-analytics\.com"],
    "meta_pixel": [r"connect\.facebook\.net", r"fbq\("],
}


def detect_signals(html):
    return sorted(k for k, pats in SIGNALS.items() if any(re.search(p, html, re.I) for p in pats))


def platform_of(signals):
    for p in ("shopify", "woocommerce", "bigcommerce", "magento"):
        if p in signals:
            return p
    return "unknown"


def page_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg", "iframe"]):
        t.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    return text[:MAX_CHARS]


def pick_second_page(html, base):
    """Best about/story/collections link on the same host, or None."""
    host = urlparse(base).netloc.replace("www.", "")
    best, best_score = None, 0
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        href = a["href"]
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = urljoin(base, href).split("#")[0].split("?")[0]
        u = urlparse(url)
        if u.netloc.replace("www.", "") != host:
            continue
        probe = (u.path + " " + a.get_text(" ")).lower()
        if re.search(r"cart|account|login|policy|policies|terms|privacy|blog", probe):
            continue
        score = 0
        if re.search(r"about|our-story|our story|story|mission", probe):
            score = 3
        elif "collections" in probe:
            score = 2
        if score > best_score:
            best, best_score = url, score
    return best


class Fetcher:
    def __init__(self, cache_dir="cache", getter=None, delay=1.0):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.http = getter or httpx.Client(headers={"User-Agent": UA}, timeout=20, follow_redirects=True)

    def _get(self, url):
        r = self.http.get(url)
        if r.status_code == 429:  # one polite retry, then give up and record the 429
            time.sleep(min(float(getattr(r, "headers", {}).get("Retry-After", 5) or 5), 10))
            r = self.http.get(url)
        return r.status_code, r.text, str(getattr(r, "url", "") or "")

    def _allowed(self, base, url):
        try:
            code, body, _ = self._get(urljoin(base, "/robots.txt"))
        except Exception:
            return True  # ponytail: unreachable robots.txt treated as absent; 5xx handled below
        if code >= 500:
            return False
        if code >= 400:
            return True
        rp = RobotFileParser()
        rp.parse(body.splitlines())
        return rp.can_fetch(UA, url)

    def fetch_site(self, domain):
        key = self.cache / (hashlib.sha1(domain.encode()).hexdigest()[:16] + ".json")
        if key.exists():
            return {**json.loads(key.read_text()), "cached": True}
        base = f"https://{domain}/"
        out = {"domain": domain, "pages": [], "signals": [], "platform": "unknown", "error": None, "cached": False, "enrichment": None}
        try:
            if not self._allowed(base, base):
                out["error"] = "blocked_by_robots"
            else:
                code, html, final = self._get(base)
                fh = urlparse(final).netloc.replace("www.", "") if final else ""
                if fh and fh != urlparse(base).netloc.replace("www.", "") and not self._allowed(final, final):
                    out["error"] = "blocked_by_robots_after_redirect"
                elif code >= 400:
                    out["error"] = f"http_{code}"
                else:
                    out["signals"] = detect_signals(html)
                    out["platform"] = platform_of(out["signals"])
                    out["enrichment"] = enrich_html(html, base)
                    out["pages"].append({"kind": "home", "url": base, "text": page_text(html)})
                    second = pick_second_page(html, base)
                    if second and self._allowed(base, second):
                        time.sleep(self.delay)
                        c2, h2, f2 = self._get(second)
                        h2host = urlparse(f2).netloc.replace("www.", "") if f2 else ""
                        moved = h2host and h2host != urlparse(base).netloc.replace("www.", "")
                        if c2 < 400 and not (moved and not self._allowed(f2, f2)):
                            out["pages"].append({"kind": "second", "url": second, "text": page_text(h2)})
                            out["enrichment"] = merge(out["enrichment"], enrich_html(h2, second))
        except Exception as e:  # network errors are data, not crashes
            out["error"] = f"fetch_error:{type(e).__name__}"
        key.write_text(json.dumps(out))
        return out
