"""First-line writer, banned-phrase filter, evidence check and claim checker."""
import re
from pathlib import Path
from .llm import FAST, WRITER, parse_json
from .profile import site_text

BANNED = [l.strip().lower() for l in (Path(__file__).resolve().parent.parent / "banned.txt").read_text().splitlines() if l.strip()]
MAX_WORDS = 30  # hard filter; the writer is asked for 24


def banned_hits(line, banned=BANNED):
    low = line.lower()
    hits = [b for b in banned if b in low]
    if "—" in line or "–" in line:
        hits.append("dash")
    if len(line.split()) > MAX_WORDS:
        hits.append(f"over_{MAX_WORDS}_words")
    return hits


def _norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def evidence_in_text(evidence, site):
    """Evidence must be a verbatim substring (whitespace and case normalised) of fetched text."""
    e = _norm(evidence)
    return len(e) >= 15 and any(e in _norm(p["text"]) for p in site["pages"])


WRITER_SYS = """You write ONE opening line for a cold outreach email to a company (not a person).
Method: pick ONE sentence from the page text. Copy it verbatim as "evidence" (30 to 220 characters).
Then write the line as a short restatement of that sentence and nothing more.
Rules:
- Every fact in the line must be inside the evidence. Add nothing from elsewhere on the page: no extra products, numbers, dates, places, reviews, awards or guarantees.
- One sentence, max 24 words, plain words, no flattery, no pitch, no question.
- Start with the company name, then what the evidence says. Do not say "your homepage".
- Do not use these phrases: {banned}.
- No dashes of any kind.
Return JSON only: {{"line": "...", "evidence": "verbatim quote", "source": "home"|"second"}}"""

CHECK_SYS = """You are a strict fact checker. You get an opening line and the evidence snippet it relies on.
Check the CONTENT words of the line: nouns, adjectives, numbers, places, years and qualifiers. Each one
must appear in the snippet or be a plain synonym of a snippet word. Ignore these, they are allowed:
the company name in any form, attribution verbs ("says", "describes", "started", "offers"), pronoun
swaps ("our" to "its", "we" to the company name), and details the line drops from the snippet.
Fail the line if it adds ANY content descriptor the snippet lacks, even a small one: for example
"for makeup" after "best foundation", "its founders" when the snippet has no founders, "activewear
fabrics" when the snippet says "fabrics".
Reply with the JSON object only, no other text, no reasoning:
{"pass": true|false, "unsupported_claims": ["..."]}"""


def write_first_line(llm, site, feedback=None, prev=None):
    sys = WRITER_SYS.format(banned=", ".join(BANNED[:12]))
    user = f"Company domain: {site['domain']}\n\nPage text:\n{site_text(site)}"
    if feedback:
        user += f"\n\nYour previous line was rejected.\nPrevious: {prev}\nProblems: {feedback}\nWrite a new line that fixes them."
    j = parse_json(llm.call("line", WRITER, sys, user, max_tokens=400, domain=site["domain"]))
    return {"line": j.get("line", "").strip(), "evidence": j.get("evidence", "").strip(), "source": j.get("source", "")}


def check_claims(llm, line, evidence, domain=""):
    try:
        j = parse_json(llm.call("check", FAST, CHECK_SYS, f"LINE: {line}\nSNIPPET: {evidence}", max_tokens=300, domain=domain))
    except ValueError:  # unparseable verdict fails closed
        return False, ["checker_unparseable"]
    return j.get("pass") is True, j.get("unsupported_claims", [])


def make_line(llm, site, max_attempts=2):
    """Write, then gate: banned filter, verbatim evidence, claim checker. One rewrite, else drop."""
    feedback, prev, first_try, first_problems = None, None, None, ""
    for attempt in range(1, max_attempts + 1):
        try:
            d = write_first_line(llm, site, feedback, prev)
        except ValueError:
            d = {"line": "", "evidence": "", "source": ""}
        problems = []
        if not d["line"]:
            problems.append("writer returned no parseable line")
        b = banned_hits(d["line"])
        if b:
            problems.append(f"banned or too long: {b}")
        if not evidence_in_text(d["evidence"], site):
            problems.append("evidence is not a verbatim quote from the page text")
        if not problems:
            ok, unsupported = check_claims(llm, d["line"], d["evidence"], site["domain"])
            if not ok:
                problems.append(f"claims not in evidence: {unsupported}")
        if first_try is None:
            first_try, first_problems = not problems, "; ".join(problems)
        if not problems:
            return {**d, "status": "pass", "attempts": attempt, "first_try_pass": first_try, "problems": "", "first_problems": first_problems}
        feedback, prev = "; ".join(problems), d["line"]
    return {**d, "status": "dropped", "attempts": max_attempts, "first_try_pass": first_try, "problems": feedback, "first_problems": first_problems}
