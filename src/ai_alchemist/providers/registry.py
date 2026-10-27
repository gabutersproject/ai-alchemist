"""Build the configured provider. Routes depend on this, not on Ollama imports."""

from ai_alchemist.config import LabSettings
from ai_alchemist.providers.ollama import OllamaProvider


def build_provider(settings: LabSettings) -> OllamaProvider:
    """Return the only provider implemented in this release."""
    return OllamaProvider(settings)
