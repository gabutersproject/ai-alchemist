"""Configuration defaults, overrides, and validation."""

import json
from pathlib import Path

import pytest

from phantomos.config import (
    EXAMPLE_MODEL,
    PhantomConfig,
    data_dir,
    is_loopback_host,
    load_config,
    save_config,
    update_config,
)
from phantomos.exceptions import ConfigError


def test_defaults_are_local_and_do_not_persist_chat():
    config = PhantomConfig()
    assert config.model == EXAMPLE_MODEL
    assert config.ollama_host == "http://127.0.0.1:11434"
    assert config.persist_conversations is False
    assert config.personality == "normal"
    assert is_loopback_host(config.ollama_host)


def test_environment_overrides_file(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"model": "from-file:latest", "personality": "subtle"}), encoding="utf-8")
    monkeypatch.setenv("PHANTOMOS_CONFIG", str(path))
    monkeypatch.setenv("PHANTOMOS_MODEL", "from-env:latest")
    monkeypatch.setenv("PHANTOMOS_PERSIST", "yes")
    loaded = load_config()
    assert loaded.model == "from-env:latest"
    assert loaded.personality == "subtle"
    assert loaded.persist_conversations is True


def test_roundtrip_save(tmp_path, monkeypatch):
    monkeypatch.setenv("PHANTOMOS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PHANTOMOS_CONFIG", raising=False)
    saved = save_config(PhantomConfig(personality="off"))
    assert saved == tmp_path / "config.json"
    assert load_config().personality == "off"


def test_update_does_not_copy_environment_overrides_into_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PHANTOMOS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PHANTOMOS_CONFIG", raising=False)
    monkeypatch.setenv("PHANTOMOS_MODEL", "from-env:latest")
    update_config("personality", "off")
    stored = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert stored["personality"] == "off"
    assert stored["model"] == EXAMPLE_MODEL
    loaded = load_config()
    assert loaded.model == "from-env:latest"
    assert loaded.personality == "off"


def test_rejects_shell_metacharacters_in_model_name():
    with pytest.raises(ConfigError):
        update_config("model", "evil;touch")
    with pytest.raises(ConfigError):
        update_config("model", "has space")


def test_rejects_unknown_setting_and_bad_personality(tmp_path, monkeypatch):
    monkeypatch.setenv("PHANTOMOS_CONFIG", str(tmp_path / "config.json"))
    with pytest.raises(ConfigError):
        update_config("not_a_setting", "1")
    with pytest.raises(ConfigError):
        update_config("personality", "spooky")


def test_invalid_json_and_unknown_keys(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setenv("PHANTOMOS_CONFIG", str(path))
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config()
    path.write_text('{"telemetry": true}', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config()


def test_rejects_credentials_in_host():
    with pytest.raises(ValueError):
        PhantomConfig(ollama_host="http://user:secret@127.0.0.1:11434")


def test_platform_data_directories():
    windows = data_dir({"LOCALAPPDATA": "C:\\Users\\me\\AppData\\Local"}, platform_name="nt")
    assert windows.name == "phantomos"
    linux = data_dir({"XDG_DATA_HOME": "/tmp/xdg-phantom"}, platform_name="posix")
    assert linux == Path("/tmp/xdg-phantom/phantomos")
    home_fallback = data_dir({}, platform_name="posix")
    assert home_fallback.name == "phantomos"


def test_loopback_detection():
    assert is_loopback_host("http://localhost:11434")
    assert is_loopback_host("http://[::1]:11434")
    assert not is_loopback_host("http://example.com:11434")
