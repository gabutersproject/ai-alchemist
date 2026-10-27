"""Ollama HTTP adapter tests. The transport is httpx.MockTransport, not a live server."""

import asyncio
import json

import httpx
import pytest

from ai_alchemist.config import LabSettings
from ai_alchemist.errors import LabError
from ai_alchemist.providers.ollama import OllamaProvider


def _provider(handler, **settings):
    return OllamaProvider(LabSettings(**settings), transport=httpx.MockTransport(handler))


def test_list_models_uses_the_tags_payload_and_marks_loopback_as_local():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        assert "authorization" not in request.headers
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "demo:latest",
                        "size": 1_500_000_000,
                        "modified_at": "2026-10-01T00:00:00Z",
                        "details": {
                            "family": "demo",
                            "parameter_size": "1B",
                            "quantization_level": "Q4",
                        },
                    }
                ]
            },
        )

    provider = _provider(handler)
    models = asyncio.run(provider.list_models())
    assert models[0].name == "demo:latest"
    assert models[0].execution == "local"
    assert models[0].available is True
    assert models[0].description == "Reported by Ollama: family demo, parameter size 1B, quantization Q4."
    assert models[0].size_label == "1.5 GB reported by Ollama"
    assert "benchmark" not in models[0].description


def test_remote_host_is_not_labeled_local():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "demo:latest"}]})

    provider = _provider(handler, ollama_host="http://models.example:11434")
    models = asyncio.run(provider.list_models())
    assert models[0].execution == "remote"
    assert models[0].description == "Ollama listed this model and did not include a description."


def test_chat_sends_no_tools_and_can_send_a_bearer_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        line = json.dumps({"message": {"role": "assistant", "content": "Hello"}, "done": False})
        done = json.dumps({"message": {"role": "assistant", "content": " there"}, "done": True})
        return httpx.Response(200, text=line + "\n" + done + "\n")

    provider = _provider(handler, ollama_token="lab-secret-token-9f3a")

    async def collect():
        parts = []
        async for fragment in provider.stream_chat(
            "demo:latest",
            [{"role": "user", "content": "Hi"}],
            asyncio.Event(),
        ):
            parts.append(fragment)
        return "".join(parts)

    assert asyncio.run(collect()) == "Hello there"
    assert seen["auth"] == "Bearer lab-secret-token-9f3a"
    assert "tools" not in seen["body"]
    assert seen["body"]["stream"] is True
    assert seen["body"]["options"]["num_predict"] == 512


def test_tool_call_is_rejected_and_not_executed():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "message": {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "ls"}}]},
            "done": True,
        }
        return httpx.Response(200, text=json.dumps(payload) + "\n")

    provider = _provider(handler)

    with pytest.raises(LabError) as caught:
        asyncio.run(_drain(provider))
    assert "did not run a command" in caught.value.message


def test_redirect_is_not_followed():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(302, headers={"Location": "http://evil.example/steal"})

    provider = _provider(handler)

    with pytest.raises(LabError) as caught:
        asyncio.run(_drain(provider))
    assert calls["count"] == 1
    assert "redirect" in caught.value.message


def test_connection_error_does_not_invent_an_answer():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(handler)
    with pytest.raises(LabError) as caught:
        asyncio.run(provider.list_models())
    assert "Could not reach Ollama" in caught.value.message
    assert "did not invent" in caught.value.message


def test_missing_model_tells_the_operator_to_pull_it():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    provider = _provider(handler)

    with pytest.raises(LabError) as caught:
        asyncio.run(_drain(provider, "missing:latest"))
    assert "ollama pull missing:latest" in caught.value.message
    assert "will not download" in caught.value.message


def test_provider_error_scrubs_the_token():
    secret = "lab-secret-token-9f3a"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=f"failed for {secret}")

    provider = _provider(handler, ollama_token=secret)

    with pytest.raises(LabError) as caught:
        asyncio.run(_drain(provider))
    assert secret not in caught.value.message
    assert "[redacted]" in caught.value.message


async def _drain(provider: OllamaProvider, model: str = "demo:latest") -> None:
    messages = [{"role": "user", "content": "Hi"}]
    async for _fragment in provider.stream_chat(model, messages, asyncio.Event()):
        pass
