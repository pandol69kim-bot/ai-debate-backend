import time
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.adapters.base import BaseAIAdapter, AIResponse
from app.core.config import settings


class OpenAIAdapter(BaseAIAdapter):
    provider = "gpt"
    display_name = "GPT-4o"

    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    async def generate(self, messages: list[dict], max_tokens: int = 1000) -> AIResponse:
        if not settings.OPENAI_API_KEY:
            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content="[OpenAI API key not configured]",
                tokens_used=0,
                latency_ms=0,
                error="API key missing",
            )

        start = time.time()
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            latency = int((time.time() - start) * 1000)
            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content=response.choices[0].message.content or "",
                tokens_used=response.usage.total_tokens if response.usage else 0,
                latency_ms=latency,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content=f"[GPT error: {str(e)}]",
                tokens_used=0,
                latency_ms=latency,
                error=str(e),
            )

    async def stream(self, messages: list[dict], max_tokens: int = 1000) -> AsyncGenerator[str, None]:
        if not settings.OPENAI_API_KEY:
            yield "[OpenAI API key not configured]"
            return

        try:
            async with self._client.chat.completions.stream(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens,
            ) as stream:
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"[GPT error: {str(e)}]"
