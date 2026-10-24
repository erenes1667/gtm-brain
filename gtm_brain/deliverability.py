"""Read-only DNS check for a sending domain: SPF, DMARC and a list of DKIM selectors. Uses `dig`. No mail is sent."""
import subprocess

SELECTORS = ["google", "selector1", "selector2", "k1", "s1", "default"]


def dig_txt(name):
    p = subprocess.run(["dig", "+short", "+time=3", "+tries=1", "TXT", name], capture_output=True, text=True, timeout=15)
    return [l.strip().strip('"') for l in p.stdout.splitlines() if l.strip()]


def check_domain(domain, txt=dig_txt, selectors=SELECTORS):
    spf = [r for r in txt(domain) if r.lower().startswith("v=spf1")]
    dmarc = [r for r in txt(f"_dmarc.{domain}") if r.lower().startswith("v=dmarc1")]
    dkim = [s for s in selectors if any("p=" in r for r in txt(f"{s}._domainkey.{domain}"))]
    pol = next((x.split("=")[1].strip() for x in dmarc[0].split(";") if x.strip().startswith("p=")), None) if dmarc else None
    issues = []
    if len(spf) != 1:
        issues.append("no SPF record" if not spf else "more than one SPF record")
    elif spf[0].rstrip().endswith("+all") or spf[0].rstrip().endswith("?all"):
        issues.append("SPF allows any sender")
    if not dmarc:
        issues.append("no DMARC record")
    elif pol == "none":
        issues.append("DMARC policy is none (monitor only)")
    if not dkim:
        issues.append("no DKIM key found on the common selectors (your sender may use another)")
    return {"domain": domain, "spf": spf[0] if spf else None, "dmarc": dmarc[0] if dmarc else None,
            "dmarc_policy": pol, "dkim_selectors_found": dkim, "issues": issues}
