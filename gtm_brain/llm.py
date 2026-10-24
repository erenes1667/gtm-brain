"""Thin Anthropic wrapper: workspace header, token and cost ledger, spend cap."""
import json, os, time
from pathlib import Path
import yaml

FAST = os.environ.get("GTM_MODEL_FAST", "claude-haiku-5-5")
WRITER = os.environ.get("GTM_MODEL_WRITER", "claude-sonnet-5-5")
PRICING = Path(__file__).resolve().parent.parent / "pricing.yaml"


# Haiku 5.5 and Sonnet 5.5 think by default and can spend the whole max_tokens on thinking, which
# returns no text. These are short extraction and writing prompts, so thinking is turned off.
# Sonnet 5.5 rejects {"type": "disabled"}; the API error says to send "between_tools".
THINKING_OFF = {"claude-haiku-5-5": {"type": "disabled"}, "claude-sonnet-5-5": {"type": "between_tools"}}


class BudgetExceeded(RuntimeError):
    pass


def load_env():
    """Fill os.environ from GTM_ENV_FILE (default ./.env). Never prints values."""
    p = Path(os.environ.get("GTM_ENV_FILE", ".env"))
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip().removeprefix("export "), v.strip().strip("'\""))


def cost_usd(model, tin, tout, pricing=None):
    pricing = pricing or yaml.safe_load(PRICING.read_text())
    r = pricing[model]
    return tin * r["input"] / 1e6 + tout * r["output"] / 1e6


def ledger_total(path):
    p = Path(path)
    if not p.exists():
        return 0.0
    return sum(json.loads(x)["usd"] for x in p.read_text().splitlines() if x.strip())


def require_keys():
    load_env()
    missing = [k for k in ("ANTHROPIC_API_KEY_PERSONAL", "ANTHROPIC_WORKSPACE_ID_PERSONAL") if not os.environ.get(k)]
    if missing:
        raise RuntimeError("Set ANTHROPIC_API_KEY_PERSONAL and ANTHROPIC_WORKSPACE_ID_PERSONAL in .env (see .env.example). Missing: " + ", ".join(missing))


class LLM:
    def __init__(self, ledger="runs/ledger.jsonl", run_log=None, budget=None, client=None):
        self.ledger = Path(ledger)
        self.run_log = Path(run_log) if run_log else None
        self.budget = float(budget if budget is not None else os.environ.get("GTM_BUDGET_USD", "6"))
        self._client = client
        self.pricing = yaml.safe_load(PRICING.read_text())

    @property
    def client(self):
        if self._client is None:
            import anthropic
            require_keys()
            self._client = anthropic.Anthropic(
                api_key=os.environ["ANTHROPIC_API_KEY_PERSONAL"],
                default_headers={"anthropic-workspace-id": os.environ["ANTHROPIC_WORKSPACE_ID_PERSONAL"]},
            )
        return self._client

    def call(self, stage, model, system, user, max_tokens=600, domain=""):
        if ledger_total(self.ledger) >= self.budget:
            raise BudgetExceeded(f"spend cap {self.budget} USD reached")
        t0 = time.time()
        extra = {"thinking": THINKING_OFF[model]} if model in THINKING_OFF else {}
        r = self.client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}], **extra,
        )
        secs = time.time() - t0
        tin, tout = r.usage.input_tokens, r.usage.output_tokens
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "stage": stage, "model": model, "domain": domain,
               "input_tokens": tin, "output_tokens": tout, "seconds": round(secs, 2),
               "usd": round(cost_usd(model, tin, tout, self.pricing), 6)}
        for p in (self.ledger, self.run_log):
            if p:
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
        return "".join(b.text for b in r.content if b.type == "text")


def parse_json(text):
    """First JSON object in text. Tolerates code fences and chatter."""
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model output")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj
