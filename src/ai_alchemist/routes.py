"""HTTP routes for the laboratory. Prompts are sent to a provider, never a shell."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from ai_alchemist import __version__
from ai_alchemist.config import (
    SettingsUpdate,
    apply_update,
    database_path,
    load_settings,
    normalize_model_name,
    public_settings,
    save_settings,
)
from ai_alchemist.errors import LabError
from ai_alchemist.history import add_experiment, clear_experiments, delete_experiment, list_experiments

router = APIRouter()


class ChatMessageIn(BaseModel):
    """One turn supplied by the browser."""

    model_config = ConfigDict(extra="forbid")

    role: str
    content: str = Field(min_length=1, max_length=16_000)


class ChatRequest(BaseModel):
    """A playground request. save is ignored unless persistence is enabled."""

    model_config = ConfigDict(extra="forbid")

    model: str
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=32)
    save: bool = False


class CompareRequest(BaseModel):
    """The same prompt for two model names. Neither side is ranked."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=16_000)
    model_a: str
    model_b: str
    save: bool = False


def _settings(request: Request) -> Any:
    return load_settings(request.app.state.config_path)


def _provider(request: Request, settings: Any) -> Any:
    return request.app.state.provider_factory(settings)


def _normalize_messages(messages: list[ChatMessageIn]) -> list[dict[str, str]]:
    if messages[-1].role != "user":
        raise LabError("The last message must be a user prompt.", status_code=422)
    cleaned: list[dict[str, str]] = []
    for message in messages:
        if message.role not in {"user", "assistant"}:
            raise LabError("Messages must use the user or assistant role.", status_code=422)
        text = message.content.strip()
        if not text:
            raise LabError("Messages cannot be empty.", status_code=422)
        cleaned.append({"role": message.role, "content": text})
    return cleaned


def _model_name(value: str) -> str:
    try:
        return normalize_model_name(value)
    except ValueError as exc:
        raise LabError(str(exc), status_code=422) from exc


async def _collect(provider: Any, model: str, messages: list[dict[str, str]]) -> str:
    cancel = asyncio.Event()
    parts: list[str] = []
    async for fragment in provider.stream_chat(model, messages, cancel):
        parts.append(fragment)
    text = "".join(parts).strip()
    if not text:
        raise LabError(
            "The model returned an empty answer. AI Alchemist did not invent a replacement answer.",
            status_code=502,
        )
    return text


def _save_turn(
    request: Request,
    settings: Any,
    *,
    save: bool,
    prompt: str,
    response: str,
    model: str,
    kind: str,
    group_id: str | None = None,
) -> tuple[str | None, str | None]:
    if not (save and settings.persist_experiments):
        return None, None
    saved = add_experiment(
        database_path(request.app.state.config_path),
        prompt=prompt,
        response=response,
        model=model,
        provider="ollama",
        kind=kind,
        group_id=group_id,
        secrets=[settings.ollama_token],
    )
    if saved is None:
        return None, "This turn was not saved because it contains the configured provider token."
    return saved, None


@router.get("/api/health")
def health() -> dict[str, str]:
    """Process health. This does not claim that a model is running."""
    return {"name": "AI Alchemist", "version": __version__, "status": "ok"}


@router.get("/api/settings")
def get_settings(request: Request) -> dict[str, Any]:
    """Public settings. The provider token is not included."""
    return public_settings(_settings(request))


@router.put("/api/settings")
def put_settings(body: SettingsUpdate, request: Request) -> dict[str, Any]:
    """Validate and store settings. The response still omits the token."""
    current = _settings(request)
    updated = apply_update(current, body)
    save_settings(updated, request.app.state.config_path)
    return public_settings(updated)


@router.post("/api/settings/test")
async def test_settings(body: SettingsUpdate, request: Request) -> dict[str, Any]:
    """Check the form against the provider without saving it."""
    current = _settings(request)
    candidate = apply_update(current, body)
    probe = await _provider(request, candidate).probe()
    return probe.as_dict()


@router.get("/api/provider")
async def provider_status(request: Request) -> dict[str, Any]:
    """Live provider status for the current saved settings."""
    settings = _settings(request)
    probe = await _provider(request, settings).probe()
    return probe.as_dict()


@router.get("/api/models")
async def models(request: Request) -> dict[str, Any]:
    """Models reported by the provider, plus whether each name is selected in settings."""
    settings = _settings(request)
    records = await _provider(request, settings).list_models()
    payload = []
    for record in records:
        item = record.as_dict()
        item["selected_default"] = record.name == settings.default_model
        item["selected_compare"] = record.name == settings.compare_model
        payload.append(item)
    return {
        "provider": "ollama",
        "provider_name": "Ollama",
        "execution": records[0].execution if records else None,
        "models": payload,
    }


@router.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> dict[str, Any]:
    """Run one completion and return it when the provider finishes."""
    settings = _settings(request)
    model = _model_name(body.model)
    messages = _normalize_messages(body.messages)
    text = await _collect(_provider(request, settings), model, messages)
    prompt = messages[-1]["content"]
    saved_id, warning = _save_turn(
        request,
        settings,
        save=body.save,
        prompt=prompt,
        response=text,
        model=model,
        kind="playground",
    )
    return {
        "model": model,
        "provider": "ollama",
        "provider_name": "Ollama",
        "execution": public_settings(settings)["execution"],
        "text": text,
        "saved_id": saved_id,
        "warning": warning,
    }


@router.post("/api/chat/stream")
async def chat_stream(body: ChatRequest, request: Request) -> StreamingResponse:
    """Stream provider tokens. Closing the connection stops reading the provider."""
    settings = _settings(request)
    model = _model_name(body.model)
    messages = _normalize_messages(body.messages)

    async def events() -> AsyncIterator[str]:
        cancel = asyncio.Event()
        parts: list[str] = []
        provider = _provider(request, settings)
        try:
            async for fragment in provider.stream_chat(model, messages, cancel):
                if await request.is_disconnected():
                    cancel.set()
                    break
                parts.append(fragment)
                yield _sse({"type": "token", "text": fragment})
        except LabError as exc:
            yield _sse({"type": "error", "message": exc.message})
            return
        except Exception:
            yield _sse(
                {
                    "type": "error",
                    "message": "The provider request failed. AI Alchemist did not invent a replacement answer.",
                }
            )
            return
        if cancel.is_set():
            yield _sse({"type": "stopped"})
            return
        text = "".join(parts).strip()
        if not text:
            yield _sse(
                {
                    "type": "error",
                    "message": "The model returned an empty answer. AI Alchemist did not invent a replacement answer.",
                }
            )
            return
        saved_id, warning = _save_turn(
            request,
            settings,
            save=body.save,
            prompt=messages[-1]["content"],
            response=text,
            model=model,
            kind="playground",
        )
        yield _sse(
            {
                "type": "done",
                "text": text,
                "model": model,
                "provider": "ollama",
                "provider_name": "Ollama",
                "execution": public_settings(settings)["execution"],
                "saved_id": saved_id,
                "warning": warning,
            }
        )

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/api/compare")
async def compare(body: CompareRequest, request: Request) -> dict[str, Any]:
    """Run the same prompt on two models. Each side fails on its own."""
    settings = _settings(request)
    model_a = _model_name(body.model_a)
    model_b = _model_name(body.model_b)
    prompt = body.prompt.strip()
    if not prompt:
        raise LabError("The prompt cannot be empty.", status_code=422)
    messages = [{"role": "user", "content": prompt}]
    group_id = uuid.uuid4().hex
    left, right = await asyncio.gather(
        _one_side(request, settings, model_a, messages, body.save, group_id),
        _one_side(request, settings, model_b, messages, body.save, group_id),
    )
    return {
        "prompt": prompt,
        "provider": "ollama",
        "provider_name": "Ollama",
        "execution": public_settings(settings)["execution"],
        "left": left,
        "right": right,
    }


async def _one_side(
    request: Request,
    settings: Any,
    model: str,
    messages: list[dict[str, str]],
    save: bool,
    group_id: str,
) -> dict[str, Any]:
    try:
        text = await _collect(_provider(request, settings), model, messages)
    except LabError as exc:
        return {
            "model": model,
            "provider": "ollama",
            "provider_name": "Ollama",
            "ok": False,
            "text": "",
            "error": exc.message,
            "saved_id": None,
            "warning": None,
        }
    saved_id, warning = _save_turn(
        request,
        settings,
        save=save,
        prompt=messages[-1]["content"],
        response=text,
        model=model,
        kind="compare",
        group_id=group_id,
    )
    return {
        "model": model,
        "provider": "ollama",
        "provider_name": "Ollama",
        "ok": True,
        "text": text,
        "error": None,
        "saved_id": saved_id,
        "warning": warning,
    }


@router.get("/api/history")
def history(request: Request) -> dict[str, Any]:
    """List experiments stored on this machine."""
    rows = list_experiments(database_path(request.app.state.config_path))
    settings = _settings(request)
    return {"experiments": rows, "persist_experiments": settings.persist_experiments}


@router.delete("/api/history/{experiment_id}")
def remove_history(experiment_id: str, request: Request) -> dict[str, Any]:
    """Delete one stored experiment."""
    if not delete_experiment(database_path(request.app.state.config_path), experiment_id):
        raise LabError("No experiment with that id.", status_code=404)
    return {"deleted": experiment_id}


@router.delete("/api/history")
def remove_all_history(request: Request) -> dict[str, int]:
    """Delete every stored experiment."""
    removed = clear_experiments(database_path(request.app.state.config_path))
    return {"deleted": removed}


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"
