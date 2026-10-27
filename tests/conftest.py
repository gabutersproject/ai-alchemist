"""Keep tests away from the developer's real AI Alchemist configuration."""

import pytest


@pytest.fixture(autouse=True)
def isolated_alchemist_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_ALCHEMIST_DATA_DIR", str(tmp_path / "appdata"))
    monkeypatch.setenv("AI_ALCHEMIST_OLLAMA_HOST", "http://127.0.0.1:9")
    monkeypatch.setenv("AI_ALCHEMIST_CONNECT_TIMEOUT", "0.4")
    monkeypatch.setenv("AI_ALCHEMIST_REQUEST_TIMEOUT", "0.8")
    monkeypatch.delenv("AI_ALCHEMIST_MODEL", raising=False)
    monkeypatch.delenv("AI_ALCHEMIST_PERSONALITY", raising=False)
    monkeypatch.delenv("AI_ALCHEMIST_PERSIST", raising=False)
    monkeypatch.delenv("AI_ALCHEMIST_CONFIG", raising=False)
    monkeypatch.delenv("AI_ALCHEMIST_STREAM", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
