"""Keep tests away from the developer machine's laboratory settings."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_alchemist.app import create_app
from tests.fakes import FakeProvider


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_ALCHEMIST_DATA_DIR", str(tmp_path / "appdata"))
    monkeypatch.delenv("AI_ALCHEMIST_CONFIG", raising=False)


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def client(tmp_path: Path, fake_provider: FakeProvider):
    app = create_app(
        config_path=tmp_path / "lab-config.json",
        provider_factory=lambda settings: fake_provider,
    )
    return TestClient(app)
