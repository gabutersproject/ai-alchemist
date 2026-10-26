"""Keep tests away from the developer's real PhantomOS configuration."""

import pytest


@pytest.fixture(autouse=True)
def isolated_phantomos_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PHANTOMOS_DATA_DIR", str(tmp_path / "appdata"))
    monkeypatch.setenv("PHANTOMOS_OLLAMA_HOST", "http://127.0.0.1:9")
    monkeypatch.setenv("PHANTOMOS_CONNECT_TIMEOUT", "0.4")
    monkeypatch.setenv("PHANTOMOS_REQUEST_TIMEOUT", "0.8")
    monkeypatch.delenv("PHANTOMOS_MODEL", raising=False)
    monkeypatch.delenv("PHANTOMOS_PERSONALITY", raising=False)
    monkeypatch.delenv("PHANTOMOS_PERSIST", raising=False)
    monkeypatch.delenv("PHANTOMOS_CONFIG", raising=False)
    monkeypatch.delenv("PHANTOMOS_STREAM", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
