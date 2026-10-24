"""MCP server exposing the seven GTM tools. Run: python -m gtm_brain.server (stdio)."""
import json, os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from . import pipeline
from .export import export_sequence as _export, NotApproved
from .fetch import Fetcher
from .icp import load_icp, score_icp as _score
from .lines import make_line
from .llm import LLM
from .profile import extract_company_profile as _profile

mcp = FastMCP("gtm-brain")
OUT = lambda: Path(os.environ.get("GTM_OUT", "runs/latest"))
_llm = lambda: LLM(os.environ.get("GTM_LEDGER", "runs/ledger.jsonl"), OUT() / "cost_log.jsonl")


@mcp.tool()
def fetch_site(domain: str) -> dict:
    """Fetch homepage plus one about/collections page. Cached, honors robots.txt. Returns text and platform signals."""
    return Fetcher(os.environ.get("GTM_CACHE", "cache")).fetch_site(domain)


@mcp.tool()
def extract_company_profile(domain: str) -> dict:
    """Haiku reads the fetched pages: category, products, price band, platform and tech hints."""
    return _profile(_llm(), fetch_site(domain))


@mcp.tool()
def score_icp(domain: str) -> dict:
    """Score a domain against icp.yaml: rule points plus an LLM judgment with reasons."""
    return _score(_llm(), load_icp(os.environ.get("GTM_ICP", "icp.yaml")), extract_company_profile(domain))


@mcp.tool()
def write_first_line(domain: str) -> dict:
    """Sonnet writes one opening line with a verbatim evidence quote. Banned-phrase, evidence and claim checks run; one rewrite, else dropped."""
    return make_line(_llm(), fetch_site(domain))


@mcp.tool()
def export_sequence(out_dir: str = "") -> dict:
    """Write Instantly and HubSpot CSVs for approved rows only. Fails if approvals.csv has no approved row."""
    try:
        return _export(out_dir or OUT())
    except NotApproved as e:
        return {"error": str(e)}


@mcp.tool()
def check_sending_domain(domain: str) -> dict:
    """Read-only DNS check of SPF, DMARC and common DKIM selectors for a sending domain."""
    from .deliverability import check_domain
    return check_domain(domain)


@mcp.tool()
def cost_report(out_dir: str = "") -> dict:
    """Token and USD totals for a run, by stage and model."""
    return pipeline.cost_report(out_dir or OUT())


if __name__ == "__main__":
    mcp.run()
