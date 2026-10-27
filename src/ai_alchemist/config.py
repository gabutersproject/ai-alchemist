"""Laboratory settings.

The optional provider token is stored in the config file and is never returned
by the API. An Ollama host URL is not allowed to carry a username or password.
"""

import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ai_alchemist.errors import LabError

_MODEL_RE = re.compile(r"^[A-Za-z0-9_.:@+/-]{1,128}$")
_APP_DIR = "ai-alchemist"


class LabSettings(BaseModel):
    """Validated settings. Unknown keys are rejected so an old file fails loudly."""

    model_config = ConfigDict(extra="forbid")

    ollama_host: str = "http://127.0.0.1:11434"
    ollama_token: str = ""
    default_model: str = ""
    compare_model: str = ""
    persist_experiments: bool = False
    max_output_tokens: int = Field(default=512, ge=16, le=4096)
    connect_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    request_timeout_seconds: float = Field(default=120.0, gt=0, le=600)

    @field_validator("ollama_host")
    @classmethod
    def _host_is_http(cls, value: str) -> str:
        return normalize_host(value)

    @field_validator("default_model", "compare_model")
    @classmethod
    def _model_token(cls, value: str) -> str:
        if value == "":
            return ""
        return normalize_model_name(value)

    @field_validator("ollama_token")
    @classmethod
    def _token_has_no_newlines(cls, value: str) -> str:
        if any(char in value for char in "\r\n"):
            raise ValueError("token must not contain newlines")
        return value.strip()


class SettingsUpdate(BaseModel):
    """A settings form. A blank token keeps the saved token unless clear_token is set."""

    model_config = ConfigDict(extra="forbid")

    ollama_host: str
    ollama_token: str | None = None
    clear_token: bool = False
    default_model: str = ""
    compare_model: str = ""
    persist_experiments: bool = False
    max_output_tokens: int = Field(default=512, ge=16, le=4096)

    @field_validator("ollama_host")
    @classmethod
    def _host_is_http(cls, value: str) -> str:
        return normalize_host(value)

    @field_validator("default_model", "compare_model")
    @classmethod
    def _model_token(cls, value: str) -> str:
        if value == "":
            return ""
        return normalize_model_name(value)

    @field_validator("ollama_token")
    @classmethod
    def _token_has_no_newlines(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if any(char in value for char in "\r\n"):
            raise ValueError("token must not contain newlines")
        return value.strip()


def normalize_host(value: str) -> str:
    """Accept an http(s) origin without embedded credentials."""
    cleaned = value.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("ollama_host must be an http or https URL with a host")
    if parsed.username or parsed.password:
        raise ValueError("ollama_host must not embed credentials; use the token field")
    if any(char in cleaned for char in "\r\n\t "):
        raise ValueError("ollama_host must not contain whitespace")
    return cleaned


def normalize_model_name(value: str) -> str:
    """Reject names that could change the meaning of a shell pull command."""
    stripped = value.strip()
    if not _MODEL_RE.fullmatch(stripped):
        raise ValueError("model must be a single token without spaces or shell characters")
    return stripped


def is_loopback_host(host: str) -> bool:
    """True when the configured host address stays on this machine."""
    hostname = (urlparse(host).hostname or "").lower().strip("[]")
    return hostname in {"127.0.0.1", "localhost", "::1"}


def execution_mode(host: str) -> str:
    """Label inference as local only when the host address is loopback."""
    return "local" if is_loopback_host(host) else "remote"


def data_dir(environ: Mapping[str, str] | None = None, *, platform_name: str | None = None) -> Path:
    """Platform data directory for this laboratory."""
    env = os.environ if environ is None else environ
    override = env.get("AI_ALCHEMIST_DATA_DIR")
    if override:
        return Path(override).expanduser()
    system = platform_name or os.name
    if system == "nt":
        local = env.get("LOCALAPPDATA")
        if local:
            return Path(local) / _APP_DIR
        return Path.home() / "AppData" / "Local" / _APP_DIR
    xdg = env.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / _APP_DIR
    return Path.home() / ".local" / "share" / _APP_DIR


def default_config_path(environ: Mapping[str, str] | None = None) -> Path:
    """Path of lab-config.json. An older inspector config.json is not read."""
    env = os.environ if environ is None else environ
    override = env.get("AI_ALCHEMIST_CONFIG")
    if override:
        return Path(override).expanduser()
    return data_dir(env) / "lab-config.json"


def database_path(config_path: Path) -> Path:
    """SQLite file stored beside the config file."""
    return config_path.parent / "experiments.sqlite"


def load_settings(path: Path | None = None) -> LabSettings:
    """Load defaults, then the JSON file. A missing file uses defaults."""
    config_path = default_config_path() if path is None else path
    if not config_path.is_file():
        return LabSettings()
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LabError(f"Cannot read settings at {config_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LabError(f"Settings file is not valid JSON: {config_path}") from exc
    if not isinstance(loaded, dict):
        raise LabError(f"Settings file must contain a JSON object: {config_path}")
    try:
        return LabSettings.model_validate(loaded)
    except ValidationError as exc:
        raise LabError(f"Settings file is invalid: {config_path}. {exc.errors()[0]['msg']}") from exc


def apply_update(current: LabSettings, update: SettingsUpdate) -> LabSettings:
    """Merge a form onto saved settings without echoing the token back."""
    if update.clear_token:
        token = ""
    elif update.ollama_token:
        token = update.ollama_token
    else:
        token = current.ollama_token
    try:
        return LabSettings.model_validate(
            {
                "ollama_host": update.ollama_host,
                "ollama_token": token,
                "default_model": update.default_model,
                "compare_model": update.compare_model,
                "persist_experiments": update.persist_experiments,
                "max_output_tokens": update.max_output_tokens,
                "connect_timeout_seconds": current.connect_timeout_seconds,
                "request_timeout_seconds": current.request_timeout_seconds,
            }
        )
    except ValidationError as exc:
        raise LabError(f"Invalid settings. {exc.errors()[0]['msg']}", status_code=422) from exc


def save_settings(settings: LabSettings, path: Path | None = None) -> Path:
    """Write settings atomically. The file mode is owner-read/write when the OS allows it."""
    config_path = default_config_path() if path is None else path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings.model_dump(mode="json"), indent=2) + "\n"
    temporary = config_path.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    _restrict(temporary)
    temporary.replace(config_path)
    _restrict(config_path)
    return config_path


def public_settings(settings: LabSettings) -> dict[str, Any]:
    """Settings safe to send to the browser. The token value is omitted."""
    return {
        "provider": "ollama",
        "provider_name": "Ollama",
        "ollama_host": settings.ollama_host,
        "token_configured": bool(settings.ollama_token),
        "default_model": settings.default_model,
        "compare_model": settings.compare_model,
        "persist_experiments": settings.persist_experiments,
        "max_output_tokens": settings.max_output_tokens,
        "execution": execution_mode(settings.ollama_host),
    }


def scrub(text: str, secret: str) -> str:
    """Remove a saved token if a provider error echoes it."""
    if secret and secret in text:
        return text.replace(secret, "[redacted]")
    return text


def _restrict(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        return
