import json, pytest


class FakeLLM:
    """Scripted stand-in for gtm_brain.llm.LLM. Replies are matched by stage, popped in order."""
    def __init__(self, replies):
        self.replies = {k: list(v) for k, v in replies.items()}
        self.calls = []

    def call(self, stage, model, system, user, max_tokens=600, domain=""):
        self.calls.append((stage, model))
        r = self.replies[stage].pop(0)
        return r if isinstance(r, str) else json.dumps(r)


@pytest.fixture
def site():
    return {"domain": "acme.test", "platform": "shopify", "signals": ["shopify", "klaviyo"], "error": None,
            "pages": [{"kind": "home", "url": "https://acme.test/", "text": "Acme makes small batch wool socks. Free shipping over $50."},
                      {"kind": "second", "url": "https://acme.test/pages/about", "text": "Founded in a garage, we cut every sock pattern by hand."}]}
