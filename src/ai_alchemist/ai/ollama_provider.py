"""Ollama over the local HTTP API. No tools, no redirects, no cloud fallback."""

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any

from ai_alchemist.ai.base import ChatMessage, Generation, ModelStatus
from ai_alchemist.config import AlchemistConfig
from ai_alchemist.exceptions import AIResponseError, AIUnavailableError

_NO_SUBSTITUTE = "AI Alchemist did not invent a replacement answer."
_REQUEST_LOCK = threading.Lock()


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect could move a prompt off the configured host."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise AIUnavailableError(
            f"The Ollama endpoint returned HTTP {code} redirect to another URL. "
            "AI Alchemist does not follow redirects, so the prompt was not sent onward."
        )


class OllamaProvider:
    """Talk to one configured Ollama server."""

    def __init__(
        self,
        config: AlchemistConfig,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self._config = config
        self._endpoint = config.ollama_host
        self._model = config.model
        if opener is None:
            self._opener = urllib.request.build_opener(_RefuseRedirect()).open
        else:
            self._opener = opener

    @property
    def model(self) -> str:
        return self._model

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def status(self) -> ModelStatus:
        """GET /api/tags. Connection failure is an unavailable model, not a guess."""
        url = f"{self._endpoint}/api/tags"
        request = urllib.request.Request(url, method="GET")
        try:
            with self._opener(request, timeout=self._config.connect_timeout_seconds) as response:
                raw = response.read()
        except AIUnavailableError:
            raise
        except urllib.error.HTTPError as exc:
            detail = _http_detail(exc, self._model)
            return ModelStatus(
                reachable=False,
                endpoint=self._endpoint,
                model=self._model,
                model_present=None,
                available_models=[],
                detail=detail,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return ModelStatus(
                reachable=False,
                endpoint=self._endpoint,
                model=self._model,
                model_present=None,
                available_models=[],
                detail=_connection_detail(self._endpoint, exc),
            )
        return self._parse_tags(raw)

    def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
        model: str | None = None,
    ) -> Generation:
        """POST /api/chat. Tool fields are never sent and tool calls are never run.

        Only one generation runs in this process at a time. A second caller gets
        an error instead of a queued request that could exhaust an 8 GB machine.
        """
        if not _REQUEST_LOCK.acquire(blocking=False):
            raise AIUnavailableError(
                "Another model request is already running in this process. "
                "AI Alchemist sends one request at a time. "
                + _NO_SUBSTITUTE
            )
        chosen = model or self._model
        try:
            return self._generate_locked(messages, stream=stream, on_token=on_token, model=chosen)
        finally:
            _REQUEST_LOCK.release()

    def _generate_locked(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool,
        on_token: Callable[[str], None] | None,
        model: str,
    ) -> Generation:
        url = f"{self._endpoint}/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "stream": stream,
            "options": {"num_predict": self._config.max_output_tokens},
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            response_cm = self._opener(request, timeout=self._config.request_timeout_seconds)
        except AIUnavailableError:
            raise
        except urllib.error.HTTPError as exc:
            raise AIUnavailableError(_http_detail(exc, model)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise AIUnavailableError(_connection_detail(self._endpoint, exc)) from exc
        with response_cm as response:
            if stream:
                text = _consume_stream(response, on_token)
            else:
                text = _consume_document(response.read())
        return Generation(text=text, model=model, source="ollama")

    def _parse_tags(self, raw: bytes) -> ModelStatus:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ModelStatus(
                reachable=True,
                endpoint=self._endpoint,
                model=self._model,
                model_present=None,
                available_models=[],
                detail=(
                    "Ollama responded, but /api/tags was not valid JSON. "
                    "Model availability was not confirmed."
                ),
            )
        if not isinstance(payload, dict):
            return ModelStatus(
                reachable=True,
                endpoint=self._endpoint,
                model=self._model,
                model_present=None,
                available_models=[],
                detail="Ollama responded, but /api/tags was not a JSON object.",
            )
        names: list[str] = []
        for item in payload.get("models") or []:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        present = self._model in names
        if present:
            detail = f"Ollama is reachable and '{self._model}' is installed locally."
        else:
            detail = (
                f"Ollama is reachable at {self._endpoint}, but '{self._model}' is not installed. "
                f"AI Alchemist will not download it. To install it yourself, run: ollama pull {self._model}"
            )
        return ModelStatus(
            reachable=True,
            endpoint=self._endpoint,
            model=self._model,
            model_present=present,
            available_models=names,
            detail=detail,
        )


def _connection_detail(endpoint: str, exc: BaseException) -> str:
    reason = getattr(exc, "reason", exc)
    return (
        f"Could not reach Ollama at {endpoint} ({reason}). "
        "AI features are unavailable until that local service is running. "
        "Repository inspection does not require a model. "
        "AI Alchemist did not contact an external model API. "
        + _NO_SUBSTITUTE
    )


def _http_detail(exc: urllib.error.HTTPError, model: str) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:
        raw = ""
    message = raw.strip()
    try:
        parsed = json.loads(raw) if raw else {}
        if isinstance(parsed, dict) and parsed.get("error"):
            message = str(parsed["error"])
    except json.JSONDecodeError:
        pass
    if exc.code in {401, 403}:
        return (
            f"The endpoint refused the request (HTTP {exc.code}). "
            "AI Alchemist does not send API keys. Point ollama_host at a local Ollama server. "
            + _NO_SUBSTITUTE
        )
    if exc.code == 404:
        return (
            f"Ollama could not find model '{model}' (HTTP 404: {message}). "
            f"AI Alchemist will not download it. Run: ollama pull {model}. "
            + _NO_SUBSTITUTE
        )
    return (
        f"Ollama returned HTTP {exc.code}: {message or 'no response body'}. "
        + _NO_SUBSTITUTE
    )


def _content_from_message(payload: dict[str, Any]) -> str:
    if "error" in payload and payload["error"]:
        raise AIResponseError(f"Ollama error: {payload['error']}. {_NO_SUBSTITUTE}")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise AIResponseError(f"Ollama returned a malformed message object. {_NO_SUBSTITUTE}")
    if message.get("tool_calls"):
        raise AIResponseError(
            "The model requested a tool call. AI Alchemist has no tools and did not execute anything. "
            + _NO_SUBSTITUTE
        )
    content = message.get("content") or ""
    if not isinstance(content, str):
        raise AIResponseError(f"Ollama returned non-text content. {_NO_SUBSTITUTE}")
    return content


def _consume_document(raw: bytes) -> str:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AIResponseError(
            f"Ollama returned a response that was not valid JSON. {_NO_SUBSTITUTE}"
        ) from exc
    if not isinstance(payload, dict):
        raise AIResponseError(f"Ollama returned JSON that was not an object. {_NO_SUBSTITUTE}")
    text = _content_from_message(payload).strip()
    if not text:
        raise AIResponseError(f"The model returned an empty answer. {_NO_SUBSTITUTE}")
    return text


def _consume_stream(response: Any, on_token: Callable[[str], None] | None) -> str:
    parts: list[str] = []
    for raw_line in response:
        if isinstance(raw_line, bytes):
            try:
                line = raw_line.decode("utf-8").strip()
            except UnicodeDecodeError as exc:
                raise AIResponseError(
                    f"Ollama returned bytes that were not UTF-8. {_NO_SUBSTITUTE}"
                ) from exc
        else:
            line = str(raw_line).strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AIResponseError(
                f"Ollama returned a streaming line that was not valid JSON. {_NO_SUBSTITUTE}"
            ) from exc
        if not isinstance(payload, dict):
            raise AIResponseError(
                f"Ollama returned a streaming JSON value that was not an object. {_NO_SUBSTITUTE}"
            )
        content = _content_from_message(payload)
        if content:
            parts.append(content)
            if on_token is not None:
                on_token(content)
        if payload.get("done") is True:
            break
    text = "".join(parts).strip()
    if not text:
        raise AIResponseError(f"The model returned an empty answer. {_NO_SUBSTITUTE}")
    return text
