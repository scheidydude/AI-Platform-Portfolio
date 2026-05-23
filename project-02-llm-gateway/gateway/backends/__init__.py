from .base import LLMBackend, CompletionResponse
from .openai_compat import OpenAICompatBackend
from ..config import BackendConfig

__all__ = ["LLMBackend", "CompletionResponse", "create_backend"]


def create_backend(config: BackendConfig, name: str) -> LLMBackend:
    if config.type == "openai_compat":
        return OpenAICompatBackend(config, name)
    raise ValueError(f"Unknown backend type '{config.type}' for backend '{name}'")
