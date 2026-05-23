from __future__ import annotations
import json
from typing import AsyncIterator

import httpx

from .base import CompletionResponse, LLMBackend
from ..config import BackendConfig
from ..models import ChatCompletionRequest


class OpenAICompatBackend(LLMBackend):
    def __init__(self, config: BackendConfig, backend_name: str) -> None:
        self._name = backend_name
        self._config = config
        headers = {}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=120.0,
        )

    @property
    def name(self) -> str:
        return self._name

    def _build_payload(self, request: ChatCompletionRequest) -> dict:
        payload = request.model_dump(exclude_none=True)
        # Override model with backend's model_id if configured
        if self._config.model_id:
            payload["model"] = self._config.model_id
        return payload

    async def complete(self, request: ChatCompletionRequest) -> CompletionResponse:
        payload = self._build_payload(request)
        payload["stream"] = False
        resp = await self._client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        content = data["choices"][0]["message"]["content"]
        return CompletionResponse(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def stream(self, request: ChatCompletionRequest) -> AsyncIterator[bytes]:
        payload = self._build_payload(request)
        payload["stream"] = True
        # Request usage in the final chunk (OpenAI-compatible servers that support it)
        payload["stream_options"] = {"include_usage": True}

        async with self._client.stream("POST", "/v1/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    yield (line + "\n").encode()

    async def close(self) -> None:
        await self._client.aclose()
