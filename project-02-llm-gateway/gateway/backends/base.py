from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

from ..models import ChatCompletionRequest


@dataclass
class CompletionResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int


class LLMBackend(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def complete(self, request: ChatCompletionRequest) -> CompletionResponse: ...

    @abstractmethod
    async def stream(self, request: ChatCompletionRequest) -> AsyncIterator[bytes]: ...

    async def close(self) -> None:
        pass
