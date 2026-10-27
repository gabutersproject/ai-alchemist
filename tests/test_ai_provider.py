"""Ollama client behavior with a fake HTTP opener. No real server is required."""

import json
import threading
import urllib.error
from io import BytesIO

import pytest

from ai_alchemist.ai.base import ChatMessage
from ai_alchemist.ai.ollama_provider import OllamaProvider
from ai_alchemist.config import AlchemistConfig
from ai_alchemist.exceptions import AIResponseError, AIUnavailableError


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __iter__(self):
        yield from self._payload.splitlines(keepends=True)

    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False


def _config() -> AlchemistConfig:
    return AlchemistConfig(model="demo:latest", ollama_host="http://127.0.0.1:9")


def test_status_and_generate_use_only_the_configured_host():
    seen = []

    def opener(request, timeout=None):
        seen.append(request)
        if request.full_url.endswith("/api/tags"):
            body = json.dumps({"models": [{"name": "demo:latest"}]}).encode()
            return FakeResponse(body)
        body = json.dumps(
            {"message": {"role": "assistant", "content": "Evidence says hello."}, "done": True}
        ).encode()
        return FakeResponse(body)

    provider = OllamaProvider(_config(), opener=opener)
    status = provider.status()
    assert status.reachable is True
    assert status.model_present is True
    generation = provider.generate([ChatMessage("user", "What is this?")])
    assert generation.text == "Evidence says hello."
    assert generation.source == "ollama"
    chat = seen[-1]
    assert chat.full_url == "http://127.0.0.1:9/api/chat"
    payload = json.loads(chat.data.decode())
    assert "tools" not in payload
    assert payload["model"] == "demo:latest"
    assert payload["options"]["num_predict"] == 512
    assert "Authorization" not in {key.lower(): value for key, value in chat.header_items()}


def test_connection_failure_is_not_a_successful_answer():
    def opener(request, timeout=None):
        raise urllib.error.URLError(ConnectionRefusedError("refused"))

    provider = OllamaProvider(_config(), opener=opener)
    status = provider.status()
    assert status.reachable is False
    assert "Connected" not in status.detail
    assert status.model_present is None
    with pytest.raises(AIUnavailableError):
        provider.generate([ChatMessage("user", "hello")])


def test_missing_model_explains_the_pull_command_and_does_not_download():
    def opener(request, timeout=None):
        if request.full_url.endswith("/api/tags"):
            return FakeResponse(json.dumps({"models": [{"name": "other:latest"}]}).encode())
        raise urllib.error.HTTPError(
            request.full_url,
            404,
            "missing",
            hdrs=None,
            fp=BytesIO(b'{"error":"model not found"}'),
        )

    provider = OllamaProvider(_config(), opener=opener)
    status = provider.status()
    assert status.reachable is True
    assert status.model_present is False
    assert "ollama pull demo:latest" in status.detail
    with pytest.raises(AIUnavailableError) as caught:
        provider.generate([ChatMessage("user", "hello")])
    assert "ollama pull demo:latest" in str(caught.value)


def test_malformed_json_is_rejected():
    def opener(request, timeout=None):
        return FakeResponse(b"this is not json")

    provider = OllamaProvider(_config(), opener=opener)
    status = provider.status()
    assert status.reachable is True
    assert status.model_present is None
    with pytest.raises(AIResponseError):
        provider.generate([ChatMessage("user", "hello")])


def test_streaming_assembles_tokens_and_tool_calls_are_not_executed():
    tokens = []

    def opener(request, timeout=None):
        lines = [
            json.dumps({"message": {"role": "assistant", "content": "Hel"}, "done": False}),
            json.dumps({"message": {"role": "assistant", "content": "lo"}, "done": True}),
        ]
        return FakeResponse(("\n".join(lines) + "\n").encode())

    provider = OllamaProvider(_config(), opener=opener)
    generation = provider.generate(
        [ChatMessage("user", "hi")],
        stream=True,
        on_token=tokens.append,
    )
    assert tokens == ["Hel", "lo"]
    assert generation.text == "Hello"

    def tool_opener(request, timeout=None):
        body = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "rm", "arguments": {}}}],
            },
            "done": True,
        }
        return FakeResponse(json.dumps(body).encode())

    provider = OllamaProvider(_config(), opener=tool_opener)
    with pytest.raises(AIResponseError) as caught:
        provider.generate([ChatMessage("user", "hi")], stream=True)
    assert "did not execute" in str(caught.value)

    def tool_with_text(request, timeout=None):
        body = {
            "message": {
                "role": "assistant",
                "content": "I would delete the repository.",
                "tool_calls": [{"function": {"name": "rm", "arguments": {}}}],
            },
            "done": True,
        }
        return FakeResponse(json.dumps(body).encode())

    provider = OllamaProvider(_config(), opener=tool_with_text)
    with pytest.raises(AIResponseError) as caught:
        provider.generate([ChatMessage("user", "hi")])
    assert "did not execute" in str(caught.value)
    assert "delete the repository" not in str(caught.value)


def test_timeout_is_reported_and_is_not_an_answer():
    def opener(request, timeout=None):
        raise TimeoutError("timed out")

    provider = OllamaProvider(_config(), opener=opener)
    with pytest.raises(AIUnavailableError) as caught:
        provider.generate([ChatMessage("user", "hello")])
    message = str(caught.value)
    assert "timed out" in message
    assert "hello" not in message.lower()
    assert "did not invent" in message.lower()


def test_a_second_request_is_refused_while_one_is_running():
    started = threading.Event()
    release = threading.Event()

    def opener(request, timeout=None):
        if request.full_url.endswith("/api/tags"):
            return FakeResponse(json.dumps({"models": [{"name": "demo:latest"}]}).encode())
        started.set()
        assert release.wait(2)
        body = json.dumps({"message": {"role": "assistant", "content": "ok"}, "done": True}).encode()
        return FakeResponse(body)

    provider = OllamaProvider(_config(), opener=opener)
    errors: list[str] = []

    def hold() -> None:
        provider.generate([ChatMessage("user", "first")])

    def overlap() -> None:
        assert started.wait(2)
        try:
            provider.generate([ChatMessage("user", "second")])
        except AIUnavailableError as exc:
            errors.append(str(exc))
        finally:
            release.set()

    first = threading.Thread(target=hold)
    second = threading.Thread(target=overlap)
    first.start()
    second.start()
    second.join(3)
    first.join(3)
    assert errors
    assert "one request at a time" in errors[0]
    assert "did not invent" in errors[0].lower()


def test_fallback_model_is_used_only_when_it_is_already_installed():
    from ai_alchemist.ai.base import ModelStatus
    from ai_alchemist.workflows import choose_inference_model

    config = AlchemistConfig()
    installed_fallback = ModelStatus(
        reachable=True,
        endpoint=config.ollama_host,
        model=config.model,
        model_present=False,
        available_models=[config.fallback_model],
        detail="recommended tag is missing",
    )
    chosen, notice = choose_inference_model(config, installed_fallback)
    assert chosen == "qwen2.5-coder:1.5b"
    assert config.model == "qwen2.5-coder:3b"
    assert notice is not None
    assert "did not download" in notice

    nothing = ModelStatus(
        reachable=True,
        endpoint=config.ollama_host,
        model=config.model,
        model_present=False,
        available_models=[],
        detail="neither tag is installed",
    )
    chosen, notice = choose_inference_model(config, nothing)
    assert chosen is None
    assert notice == "neither tag is installed"

    disabled = config.model_copy(update={"use_fallback": False})
    chosen, notice = choose_inference_model(disabled, installed_fallback)
    assert chosen is None


def test_empty_model_answer_is_rejected():
    def opener(request, timeout=None):
        body = json.dumps({"message": {"role": "assistant", "content": "  "}, "done": True})
        return FakeResponse(body.encode())

    provider = OllamaProvider(_config(), opener=opener)
    with pytest.raises(AIResponseError):
        provider.generate([ChatMessage("user", "hi")])
