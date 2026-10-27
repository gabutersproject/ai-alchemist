"""Local model providers. The default and only built-in provider is Ollama."""

from ai_alchemist.ai.base import AIProvider, ChatMessage, Generation, ModelStatus
from ai_alchemist.ai.ollama_provider import OllamaProvider

__all__ = [
    "AIProvider",
    "ChatMessage",
    "Generation",
    "ModelStatus",
    "OllamaProvider",
]
