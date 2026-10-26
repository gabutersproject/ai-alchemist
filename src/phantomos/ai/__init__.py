"""Local model providers. The default and only built-in provider is Ollama."""

from phantomos.ai.base import AIProvider, ChatMessage, Generation, ModelStatus
from phantomos.ai.ollama_provider import OllamaProvider

__all__ = [
    "AIProvider",
    "ChatMessage",
    "Generation",
    "ModelStatus",
    "OllamaProvider",
]
