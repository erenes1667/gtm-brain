

def test_missing_keys_fail_clearly(monkeypatch, tmp_path):
    import pytest
    from gtm_brain.llm import require_keys
    monkeypatch.setenv("GTM_ENV_FILE", str(tmp_path / "none"))
    monkeypatch.delenv("ANTHROPIC_API_KEY_PERSONAL", raising=False)
    monkeypatch.delenv("ANTHROPIC_WORKSPACE_ID_PERSONAL", raising=False)
    with pytest.raises(RuntimeError, match="see .env.example"):
        require_keys()
