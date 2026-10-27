"""Settings validation and secret handling."""

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_alchemist.config import (
    LabSettings,
    SettingsUpdate,
    apply_update,
    data_dir,
    execution_mode,
    is_loopback_host,
    load_settings,
    public_settings,
    save_settings,
)
from ai_alchemist.errors import LabError


def test_defaults_are_loopback_and_do_not_persist():
    settings = LabSettings()
    assert settings.ollama_host == "http://127.0.0.1:11434"
    assert settings.ollama_token == ""
    assert settings.persist_experiments is False
    assert execution_mode(settings.ollama_host) == "local"
    assert is_loopback_host("http://[::1]:11434")
    assert execution_mode("http://example.com:11434") == "remote"


def test_host_rejects_embedded_credentials():
    with pytest.raises(ValidationError):
        LabSettings(ollama_host="http://user:s3cret@127.0.0.1:11434")


def test_model_names_reject_shell_characters():
    with pytest.raises(ValidationError):
        LabSettings(default_model="bad;name")
    with pytest.raises(ValidationError):
        LabSettings(compare_model="has space")


def test_blank_token_keeps_the_saved_token_until_cleared(tmp_path: Path):
    current = LabSettings(ollama_token="lab-secret-token-9f3a")
    kept = apply_update(
        current,
        SettingsUpdate(ollama_host="http://127.0.0.1:11434", ollama_token=""),
    )
    assert kept.ollama_token == "lab-secret-token-9f3a"
    cleared = apply_update(
        kept,
        SettingsUpdate(ollama_host="http://127.0.0.1:11434", clear_token=True),
    )
    assert cleared.ollama_token == ""
    path = save_settings(cleared, tmp_path / "lab-config.json")
    assert load_settings(path).ollama_token == ""


def test_public_settings_omit_the_token():
    shown = public_settings(LabSettings(ollama_token="lab-secret-token-9f3a"))
    assert shown["token_configured"] is True
    assert "lab-secret-token-9f3a" not in json.dumps(shown)


def test_save_restricts_file_mode(tmp_path: Path):
    path = save_settings(LabSettings(ollama_token="lab-secret-token-9f3a"), tmp_path / "lab-config.json")
    assert "lab-secret-token-9f3a" in path.read_text(encoding="utf-8")
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600


def test_invalid_json_is_reported(tmp_path: Path):
    path = tmp_path / "lab-config.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(LabError):
        load_settings(path)


def test_platform_data_directory():
    windows = data_dir({"LOCALAPPDATA": "C:\\Users\\me\\AppData\\Local"}, platform_name="nt")
    assert windows.name == "ai-alchemist"
    linux = data_dir({"XDG_DATA_HOME": "/tmp/xdg-data"}, platform_name="posix")
    assert linux == Path("/tmp/xdg-data/ai-alchemist")
