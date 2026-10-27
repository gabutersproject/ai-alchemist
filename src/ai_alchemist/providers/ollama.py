"""Ollama adapter.

Requests go only to the configured host. Redirects are not followed. Tool calls
are rejected and never executed. An empty or malformed body is an error, not a
made-up answer.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ai_alchemist.config import LabSettings, execution_mode, scrub
from ai_alchemist.errors import LabError
from ai_alchemist.providers.base import ModelRecord, ProbeResult

_NO_SUBSTITUTE = "AI Alchemist did not invent a replacement answer."


class OllamaProvider:
    """Talk to one Ollama-compatible HTTP server."""

    id = "ollama"
    display_name = "Ollama"

    def __init__(self, settings: LabSettings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._settings = settings
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            connect=self._settings.connect_timeout_seconds,
            read=self._settings.request_timeout_seconds,
            write=30.0,
            pool=30.0,
        )
        headers = {"Accept": "application/json"}
        if self._settings.ollama_token:
            headers["Authorization"] = f"Bearer {self._settings.ollama_token}"
        return httpx.AsyncClient(
            transport=self._transport,
            timeout=timeout,
            follow_redirects=False,
            headers=headers,
        )

    async def probe(self) -> ProbeResult:
        """GET /api/tags and report what that call actually returned."""
        host = self._settings.ollama_host
        execution = execution_mode(host)
        try:
            models = await self.list_models()
        except LabError as exc:
            return ProbeResult(
                connected=False,
                provider=self.id,
                provider_name=self.display_name,
                execution=execution,
                host=host,
                model_count=None,
                detail=exc.message,
            )
        count = len(models)
        noun = "model" if count == 1 else "models"
        return ProbeResult(
            connected=True,
            provider=self.id,
            provider_name=self.display_name,
            execution=execution,
            host=host,
            model_count=count,
            detail=f"Ollama responded with {count} {noun}.",
        )

    async def list_models(self) -> list[ModelRecord]:
        """Return the tags Ollama listed. Availability means the tag was in that list."""
        url = f"{self._settings.ollama_host}/api/tags"
        try:
            async with self._client() as client:
                response = await client.get(url)
        except httpx.TimeoutException as exc:
            raise LabError(self._down_message(exc), status_code=503) from exc
        except httpx.HTTPError as exc:
            raise LabError(self._down_message(exc), status_code=503) from exc
        self._refuse_redirect(response)
        if response.status_code >= 400:
            raise LabError(self._http_message(response, model=None), status_code=502)
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise LabError(
                "Ollama responded, but /api/tags was not valid JSON. Model availability was not confirmed.",
                status_code=502,
            ) from exc
        if not isinstance(payload, dict):
            raise LabError("Ollama responded, but /api/tags was not a JSON object.", status_code=502)
        execution = execution_mode(self._settings.ollama_host)
        records: list[ModelRecord] = []
        for item in payload.get("models") or []:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            records.append(
                ModelRecord(
                    name=item["name"],
                    provider=self.id,
                    provider_name=self.display_name,
                    available=True,
                    execution=execution,
                    description=_describe(item),
                    size_label=_size_label(item.get("size")),
                    modified_at=item.get("modified_at") if isinstance(item.get("modified_at"), str) else None,
                )
            )
        return records

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        cancel: Any,
    ) -> AsyncIterator[str]:
        """POST /api/chat and yield incremental text. No tools field is sent."""
        url = f"{self._settings.ollama_host}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"num_predict": self._settings.max_output_tokens},
        }
        try:
            async with self._client() as client:
                async with client.stream("POST", url, json=payload) as response:
                    self._refuse_redirect(response)
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise LabError(
                            self._http_message(response, model=model, body=body),
                            status_code=502,
                        )
                    async for line in response.aiter_lines():
                        if cancel.is_set():
                            break
                        fragment = _fragment(line)
                        if fragment:
                            yield fragment
        except LabError:
            raise
        except httpx.TimeoutException as exc:
            raise LabError(self._down_message(exc), status_code=503) from exc
        except httpx.HTTPError as exc:
            raise LabError(self._down_message(exc), status_code=503) from exc

    def _refuse_redirect(self, response: httpx.Response) -> None:
        if response.status_code in {301, 302, 303, 307, 308}:
            raise LabError(
                "The Ollama endpoint returned a redirect. AI Alchemist does not follow redirects, "
                "so the prompt was not sent onward. "
                + _NO_SUBSTITUTE,
                status_code=502,
            )

    def _down_message(self, exc: BaseException) -> str:
        return scrub(
            f"Could not reach Ollama at {self._settings.ollama_host} ({exc}). "
            "Start it with `ollama serve`, or change the host in Settings. "
            + _NO_SUBSTITUTE,
            self._settings.ollama_token,
        )

    def _http_message(self, response: httpx.Response, *, model: str | None, body: bytes | None = None) -> str:
        raw = ""
        if body is not None:
            raw = body.decode("utf-8", errors="replace")
        elif response.content:
            raw = response.text
        message = _error_text(raw)
        message = scrub(message, self._settings.ollama_token)
        if response.status_code in {401, 403}:
            if self._settings.ollama_token:
                return (
                    f"The endpoint refused the configured token (HTTP {response.status_code}). "
                    + _NO_SUBSTITUTE
                )
            return (
                f"The endpoint requires authentication (HTTP {response.status_code}) and no token is configured. "
                + _NO_SUBSTITUTE
            )
        if response.status_code == 404 and model:
            return (
                f"Ollama does not have model '{model}' (HTTP 404). "
                f"AI Alchemist will not download it. Pull it yourself with: ollama pull {model}. "
                + _NO_SUBSTITUTE
            )
        detail = message or "no response body"
        return f"Ollama returned HTTP {response.status_code}: {detail}. " + _NO_SUBSTITUTE


def _error_text(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text[:400]
    if isinstance(parsed, dict) and parsed.get("error"):
        return str(parsed["error"])[:400]
    return text[:400]


def _describe(item: dict[str, Any]) -> str:
    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    bits: list[str] = []
    family = details.get("family")
    params = details.get("parameter_size")
    quant = details.get("quantization_level")
    if isinstance(family, str) and family.strip():
        bits.append(f"family {family.strip()}")
    if isinstance(params, str) and params.strip():
        bits.append(f"parameter size {params.strip()}")
    if isinstance(quant, str) and quant.strip():
        bits.append(f"quantization {quant.strip()}")
    if bits:
        return "Reported by Ollama: " + ", ".join(bits) + "."
    return "Ollama listed this model and did not include a description."


def _size_label(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} GB reported by Ollama"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} MB reported by Ollama"
    return f"{value} B reported by Ollama"


def _fragment(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LabError(
            f"Ollama returned a streaming line that was not valid JSON. {_NO_SUBSTITUTE}",
            status_code=502,
        ) from exc
    if not isinstance(payload, dict):
        raise LabError(
            f"Ollama returned a streaming JSON value that was not an object. {_NO_SUBSTITUTE}",
            status_code=502,
        )
    if payload.get("error"):
        raise LabError(f"Ollama error: {payload['error']}. {_NO_SUBSTITUTE}", status_code=502)
    message = payload.get("message")
    if message is None and payload.get("done") is True:
        return ""
    if not isinstance(message, dict):
        raise LabError(f"Ollama returned a malformed message object. {_NO_SUBSTITUTE}", status_code=502)
    if message.get("tool_calls"):
        raise LabError(
            "The model requested a tool call. AI Alchemist has no tools and did not run a command. "
            + _NO_SUBSTITUTE,
            status_code=502,
        )
    content = message.get("content") or ""
    if not isinstance(content, str):
        raise LabError(f"Ollama returned non-text content. {_NO_SUBSTITUTE}", status_code=502)
    return content
