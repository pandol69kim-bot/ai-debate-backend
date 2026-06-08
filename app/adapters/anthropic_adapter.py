import time
from typing import AsyncGenerator
import anthropic
from app.adapters.base import BaseAIAdapter, AIResponse
from app.core.config import settings


class AnthropicAdapter(BaseAIAdapter):
    provider = "claude"
    display_name = "Claude Opus"

    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    def _convert_messages(self, messages: list[dict]) -> tuple[str | None, list[dict]]:
        system = None
        converted = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                converted.append({"role": msg["role"], "content": msg["content"]})
        return system, converted

    async def generate(self, messages: list[dict], max_tokens: int = 1000) -> AIResponse:
        if not settings.ANTHROPIC_API_KEY:
            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content="[Anthropic API key not configured]",
                tokens_used=0,
                latency_ms=0,
                error="API key missing",
            )

        start = time.time()
        system, converted = self._convert_messages(messages)
        try:
            kwargs = {
                "model": self._model,
                "messages": converted,
                "max_tokens": max_tokens,
            }
            if system:
                kwargs["system"] = system

            response = await self._client.messages.create(**kwargs)
            latency = int((time.time() - start) * 1000)
            content = response.content[0].text if response.content else ""
            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content=content,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                latency_ms=latency,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content=f"[Claude error: {str(e)}]",
                tokens_used=0,
                latency_ms=latency,
                error=str(e),
            )

    async def stream(self, messages: list[dict], max_tokens: int = 1000) -> AsyncGenerator[str, None]:
        if not settings.ANTHROPIC_API_KEY:
            yield "[Anthropic API key not configured]"
            return

        system, converted = self._convert_messages(messages)
        try:
            kwargs = {
                "model": self._model,
                "messages": converted,
                "max_tokens": max_tokens,
            }
            if system:
                kwargs["system"] = system

            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"[Claude error: {str(e)}]"
