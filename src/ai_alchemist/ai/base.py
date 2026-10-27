"""Provider interface. Implementations must not invent answers."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatMessage:
    """One chat turn. Repository evidence belongs in user messages, not system text."""

    role: str
    content: str


@dataclass(frozen=True)
class Generation:
    """Text that actually came back from a model service."""

    text: str
    model: str
    source: str


@dataclass
class ModelStatus:
    """Result of a real connectivity check."""

    reachable: bool
    endpoint: str
    model: str
    model_present: bool | None
    available_models: list[str]
    detail: str


class AIProvider(Protocol):
    """Local inference. Callers must not treat an exception as a successful answer."""

    def status(self) -> ModelStatus:
        """Check the service and whether the configured model is installed."""

    def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
    ) -> Generation:
        """Generate a completion. Raise if the service or the response is unusable."""
