"""Configuration for local inference and repository limits.

The example model is a configuration value, not a promise that it is installed
or that it fits the current machine. AI Alchemist never downloads weights.
"""

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ai_alchemist.exceptions import ConfigError

Personality = Literal["subtle", "normal", "cursed", "off"]
PERSONALITY_LEVELS: tuple[str, ...] = ("subtle", "normal", "cursed", "off")

# Recommended tag for an 8 GB machine when the operator accepts its license.
# Upstream Qwen2.5-Coder 3B weights are under the Qwen Research License, not
# Apache-2.0. The 1.5B checkpoint is Apache-2.0 and is the fallback when the
# recommended tag is not installed. Confirm the license of the exact tag you pull.
# Neither tag is a promise that inference will be comfortable on every 8 GB machine.
RECOMMENDED_MODEL = "qwen2.5-coder:3b"
FALLBACK_MODEL = "qwen2.5-coder:1.5b"
EXAMPLE_MODEL = RECOMMENDED_MODEL

_MODEL_RE_TEXT = r"^[A-Za-z0-9_.:@+/-]{1,128}$"
_ENV_FIELDS = {
    "AI_ALCHEMIST_MODEL": "model",
    "AI_ALCHEMIST_FALLBACK_MODEL": "fallback_model",
    "AI_ALCHEMIST_USE_FALLBACK": "use_fallback",
    "AI_ALCHEMIST_OLLAMA_HOST": "ollama_host",
    "AI_ALCHEMIST_MAX_OUTPUT_TOKENS": "max_output_tokens",
    "AI_ALCHEMIST_PERSONALITY": "personality",
    "AI_ALCHEMIST_PERSIST": "persist_conversations",
    "AI_ALCHEMIST_CONNECT_TIMEOUT": "connect_timeout_seconds",
    "AI_ALCHEMIST_REQUEST_TIMEOUT": "request_timeout_seconds",
    "AI_ALCHEMIST_STREAM": "stream",
}


class AlchemistConfig(BaseModel):
    """Validated settings. Unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")

    model: str = EXAMPLE_MODEL
    fallback_model: str = FALLBACK_MODEL
    use_fallback: bool = True
    ollama_host: str = "http://127.0.0.1:11434"
    max_output_tokens: int = Field(default=512, gt=16, le=4096)
    connect_timeout_seconds: float = Field(default=3.0, gt=0, le=60)
    request_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    personality: Personality = "normal"
    persist_conversations: bool = False
    stream: bool = True
    max_file_bytes: int = Field(default=200_000, gt=0, le=5_000_000)
    max_files_in_context: int = Field(default=8, gt=0, le=100)
    max_context_chars: int = Field(default=24_000, gt=1_000, le=200_000)
    max_history_messages: int = Field(default=16, ge=0, le=100)
    max_tree_depth: int = Field(default=3, ge=1, le=8)
    max_tree_entries: int = Field(default=80, ge=10, le=500)
    history_limit: int = Field(default=20, ge=1, le=200)

    @field_validator("model", "fallback_model")
    @classmethod
    def _model_is_a_single_token(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or any(char.isspace() for char in stripped):
            raise ValueError("model must be a single token without whitespace")
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:@+/-")
        if any(char not in allowed for char in stripped):
            raise ValueError(
                "model may contain only letters, numbers, and _ . : @ + / - "
                "so the suggested pull command cannot change shell meaning"
            )
        return stripped

    @field_validator("ollama_host")
    @classmethod
    def _host_is_http(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("ollama_host must be an http or https URL with a host")
        if parsed.username or parsed.password:
            raise ValueError("ollama_host must not embed credentials")
        if any(char in cleaned for char in "\r\n\t "):
            raise ValueError("ollama_host must not contain whitespace")
        return cleaned


def is_loopback_host(host: str) -> bool:
    """True when prompts would stay on the local machine by address."""
    hostname = (urlparse(host).hostname or "").lower().strip("[]")
    return hostname in {"127.0.0.1", "localhost", "::1"}


def data_dir(environ: Mapping[str, str] | None = None, *, platform_name: str | None = None) -> Path:
    """Platform-aware application data directory."""
    env = os.environ if environ is None else environ
    override = env.get("AI_ALCHEMIST_DATA_DIR")
    if override:
        return Path(override).expanduser()
    system = platform_name or os.name
    if system == "nt":
        local = env.get("LOCALAPPDATA")
        if local:
            return Path(local) / "ai-alchemist"
        return Path.home() / "AppData" / "Local" / "ai-alchemist"
    xdg = env.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "ai-alchemist"
    return Path.home() / ".local" / "share" / "ai-alchemist"


def config_path(environ: Mapping[str, str] | None = None) -> Path:
    """Path of the JSON configuration file."""
    env = os.environ if environ is None else environ
    override = env.get("AI_ALCHEMIST_CONFIG")
    if override:
        return Path(override).expanduser()
    return data_dir(env) / "config.json"


def database_path(environ: Mapping[str, str] | None = None) -> Path:
    """SQLite file used only when conversation persistence is enabled."""
    return data_dir(environ) / "conversations.sqlite"


def _parse_bool(raw: str) -> bool:
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"Expected a boolean value, received '{raw}'.")


def _coerce_env(field: str, raw: str) -> Any:
    annotation = AlchemistConfig.model_fields[field].annotation
    if annotation is bool:
        return _parse_bool(raw)
    if annotation is int:
        try:
            return int(raw)
        except ValueError as exc:
            raise ConfigError(f"{field} must be an integer.") from exc
    if annotation is float:
        try:
            return float(raw)
        except ValueError as exc:
            raise ConfigError(f"{field} must be a number.") from exc
    return raw


def overriding_env_var(field: str, environ: Mapping[str, str] | None = None) -> str | None:
    """Return the environment variable that overrides `field`, if one is set."""
    env = os.environ if environ is None else environ
    for env_key, name in _ENV_FIELDS.items():
        if name == field and env.get(env_key):
            return env_key
    return None


def _read_config_file(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return the JSON object on disk. Environment variables are not included."""
    env = os.environ if environ is None else environ
    path = config_path(env)
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Cannot read configuration file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Configuration file is not valid JSON: {path} ({exc})") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"Configuration file must contain a JSON object: {path}")
    return loaded


def load_config(environ: Mapping[str, str] | None = None) -> AlchemistConfig:
    """Load defaults, then the config file, then environment overrides."""
    env = os.environ if environ is None else environ
    data = _read_config_file(env)
    for env_key, field in _ENV_FIELDS.items():
        raw = env.get(env_key)
        if raw is not None and raw != "":
            data[field] = _coerce_env(field, raw)
    try:
        return AlchemistConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration: {exc}") from exc


def save_config(config: AlchemistConfig, environ: Mapping[str, str] | None = None) -> Path:
    """Write configuration atomically. Environment variables are not stored."""
    path = config_path(environ)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(config.model_dump(mode="json"), indent=2) + "\n"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
    return path


def update_config(key: str, raw_value: str, environ: Mapping[str, str] | None = None) -> AlchemistConfig:
    """Validate and persist one setting."""
    if key not in AlchemistConfig.model_fields:
        known = ", ".join(sorted(AlchemistConfig.model_fields))
        raise ConfigError(f"Unknown setting '{key}'. Known settings: {known}")
    current = _read_config_file(environ)
    current[key] = _coerce_env(key, raw_value)
    try:
        updated = AlchemistConfig.model_validate(current)
    except ValidationError as exc:
        raise ConfigError(f"Invalid value for {key}: {exc}") from exc
    save_config(updated, environ)
    return updated


def ensure_data_dir_writable(directory: Path) -> tuple[bool, str]:
    """Create the data directory and probe it with a temporary file."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".ai-alchemist-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return False, f"{directory} is not writable: {exc}"
    return True, str(directory)
