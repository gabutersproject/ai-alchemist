"""In-memory provider for API tests. It does not invent replies inside the application."""

import asyncio

from ai_alchemist.errors import LabError
from ai_alchemist.providers.base import ModelRecord, ProbeResult


class FakeProvider:
    """A stand-in whose replies are chosen by the test."""

    id = "ollama"
    display_name = "Ollama"

    def __init__(self) -> None:
        self.down = False
        self.fail_models: set[str] = set()
        self.replies: dict[str, str] = {}
        self.default_reply = "Measured reply."
        self.calls: list[tuple[str, list[dict[str, str]]]] = []
        self.execution = "local"
        self.host = "http://127.0.0.1:11434"

    async def probe(self) -> ProbeResult:
        if self.down:
            return ProbeResult(
                connected=False,
                provider=self.id,
                provider_name=self.display_name,
                execution=self.execution,
                host=self.host,
                model_count=None,
                detail="Could not reach Ollama at http://127.0.0.1:11434.",
            )
        return ProbeResult(
            connected=True,
            provider=self.id,
            provider_name=self.display_name,
            execution=self.execution,
            host=self.host,
            model_count=2,
            detail="Ollama responded with 2 models.",
        )

    async def list_models(self) -> list[ModelRecord]:
        if self.down:
            raise LabError("Could not reach Ollama at http://127.0.0.1:11434.", status_code=503)
        return [
            ModelRecord(
                name="demo:a",
                provider=self.id,
                provider_name=self.display_name,
                available=True,
                execution=self.execution,
                description="Reported by the test double.",
            ),
            ModelRecord(
                name="demo:b",
                provider=self.id,
                provider_name=self.display_name,
                available=True,
                execution=self.execution,
                description="Reported by the test double.",
            ),
        ]

    async def stream_chat(self, model: str, messages: list[dict[str, str]], cancel: asyncio.Event):
        self.calls.append((model, messages))
        if self.down:
            raise LabError("Could not reach Ollama at http://127.0.0.1:11434.", status_code=503)
        if model in self.fail_models:
            raise LabError(
                f"Ollama does not have model '{model}'. AI Alchemist will not download it.",
                status_code=502,
            )
        if cancel.is_set():
            return
        yield self.replies.get(model, self.default_reply)
