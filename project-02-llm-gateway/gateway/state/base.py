from abc import ABC, abstractmethod


class QuotaStore(ABC):
    @abstractmethod
    async def init(self) -> None: ...

    @abstractmethod
    async def get_usage(self, team: str, month: str) -> int: ...

    @abstractmethod
    async def increment(self, team: str, month: str, tokens: int) -> int:
        """Atomically add tokens; return new total."""
        ...

    @abstractmethod
    async def reset(self, team: str, month: str) -> None: ...

    @abstractmethod
    async def log_request(
        self,
        *,
        request_id: str,
        team: str,
        model: str,
        backend: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_tokens: int,
        latency_ms: int,
        status: str,
    ) -> None: ...

    @abstractmethod
    async def get_all_usage(self, month: str) -> list[dict]: ...
