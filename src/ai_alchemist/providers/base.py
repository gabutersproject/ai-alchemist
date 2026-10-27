"""Provider-neutral records. Adapters fill these from real API responses."""

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass
class ModelRecord:
    """One model a provider reported. Fields are omitted rather than invented."""

    name: str
    provider: str
    provider_name: str
    available: bool
    execution: str
    description: str
    size_label: str | None = None
    modified_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProbeResult:
    """A live check of one provider. model_count is None when the check failed."""

    connected: bool
    provider: str
    provider_name: str
    execution: str
    host: str
    model_count: int | None
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChatProvider(Protocol):
    """The surface the routes use. A new provider implements this, not the UI."""

    id: str
    display_name: str

    async def probe(self) -> ProbeResult:
        """Check connectivity without inventing a model list."""

    async def list_models(self) -> list[ModelRecord]:
        """Return models the provider itself reports."""

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        cancel: Any,
    ) -> Any:
        """Yield text fragments from a real generation."""
