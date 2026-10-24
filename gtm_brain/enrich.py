"""Company-level enrichment from HTML already fetched. Rules only, no requests, no LLM."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# Matched against script src, link href and inline script text (not visible page text).
TOOLS = {
    "platform": {"shopify": r"cdn\.shopify\.com|Shopify\.theme|/cdn/shop/", "woocommerce": r"woocommerce",
                 "bigcommerce": r"cdn\d*\.bigcommerce\.com", "magento": r"Magento|/static/version\d+/",
                 "squarespace": r"static1\.squarespace\.com|squarespace-cdn", "wix": r"static\.parastorage\.com|wixstatic\.com"},
    "email_sms": {"klaviyo": r"klaviyo\.com", "attentive": r"attn\.tv|attentivemobile", "postscript": r"postscript\.io",
                  "omnisend": r"omnisnippet|omnisend", "mailchimp": r"chimpstatic\.com|mailchimp", "privy": r"privy\.com|widget\.privy"},
    "reviews": {"yotpo": r"yotpo", "judge.me": r"judge\.me|judgeme", "okendo": r"okendo", "stamped": r"stamped\.io",
                "loox": r"loox\.io", "trustpilot": r"trustpilot", "bazaarvoice": r"bazaarvoice|bvapi"},
    "helpdesk": {"gorgias": r"gorgias", "zendesk": r"zdassets\.com|zendesk", "intercom": r"intercom(cdn)?\.", "freshdesk": r"freshdesk|freshchat",
                 "helpscout": r"helpscout|beacon-v2", "gladly": r"gladly\.com", "kustomer": r"kustomer"},
    "analytics": {"google_tag": r"googletagmanager\.com|google-analytics\.com", "meta_pixel": r"connect\.facebook\.net|fbq\(",
                  "tiktok_pixel": r"analytics\.tiktok\.com|ttq\.", "pinterest_tag": r"s\.pinimg\.com/ct|pintrk",
                  "segment": r"cdn\.segment\.com", "hotjar": r"hotjar", "triple_whale": r"triplewhale|northbeam", "mixpanel": r"mixpanel", "amplitude": r"amplitude"},
}
CAREERS_TEXT = re.compile(r"^\s*(careers?|jobs|we'?re hiring|join (us|our team)|work with us)\s*$", re.I)
CAREERS_PATH = re.compile(r"/(careers?|jobs|join-us|work-with-us)(/|$)", re.I)
JOB_BOARDS = re.compile(r"(greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|breezy\.hr|bamboohr\.com/careers)", re.I)


def _code_blob(soup):
    parts = [t.get("src", "") for t in soup.find_all("script")] + [t.string or "" for t in soup.find_all("script")]
    parts += [t.get("href", "") for t in soup.find_all("link")]
    return "\n".join(parts)


def clean_url(url):
    """A malformed href can embed a second URL (seen on a real site). Keep the embedded one."""
    i = max(url.rfind("https:/"), url.rfind("http:/"))
    return re.sub(r"^(https?):/(?!/)", r"\1://", url[i:]) if i > 8 else url


def careers_link(soup, base):
    for a in soup.find_all("a", href=True):
        url = clean_url(urljoin(base, a["href"]))
        if CAREERS_PATH.search(url.split("?")[0]) or JOB_BOARDS.search(url) or CAREERS_TEXT.search(a.get_text(" ")):
            return url.split("#")[0]
    return None


def enrich_html(html, base):
    soup = BeautifulSoup(html, "html.parser")
    blob = _code_blob(soup)
    found = {k: sorted(n for n, p in tools.items() if re.search(p, blob, re.I)) for k, tools in TOOLS.items()}
    return {"platform": (found.pop("platform") or ["unknown"])[0], **found, "careers_link": careers_link(soup, base)}


def merge(a, b):
    """Combine two page results: union the tool lists, keep the first platform and careers link found."""
    if not a:
        return b
    out = {k: sorted(set(a[k]) | set(b[k])) for k in ("email_sms", "reviews", "helpdesk", "analytics")}
    out["platform"] = a["platform"] if a["platform"] != "unknown" else b["platform"]
    out["careers_link"] = a["careers_link"] or b["careers_link"]
    return out
