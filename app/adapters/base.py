from abc import ABC, abstractmethod
from typing import AsyncGenerator
from dataclasses import dataclass


@dataclass
class AIResponse:
    provider: str
    display_name: str
    content: str
    tokens_used: int
    latency_ms: int
    error: str | None = None


class BaseAIAdapter(ABC):
    provider: str
    display_name: str

    @abstractmethod
    async def generate(self, messages: list[dict], max_tokens: int = 1000) -> AIResponse:
        """Generate a single complete response."""

    @abstractmethod
    async def stream(self, messages: list[dict], max_tokens: int = 1000) -> AsyncGenerator[str, None]:
        """Stream tokens one by one."""

    def build_system_message(self, content: str) -> dict:
        return {"role": "system", "content": content}

    def build_user_message(self, content: str) -> dict:
        return {"role": "user", "content": content}

    def build_assistant_message(self, content: str) -> dict:
        return {"role": "assistant", "content": content}
