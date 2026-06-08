from app.adapters.base import BaseAIAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.gemini_adapter import GeminiAdapter

_adapters: dict[str, BaseAIAdapter] = {
    "gpt": OpenAIAdapter(),
    "claude": AnthropicAdapter(),
    "gemini": GeminiAdapter(),
}


def get_adapter(provider: str) -> BaseAIAdapter | None:
    return _adapters.get(provider)


def get_all_adapters() -> list[BaseAIAdapter]:
    return list(_adapters.values())


def get_adapters_by_providers(providers: list[str]) -> list[BaseAIAdapter]:
    return [_adapters[p] for p in providers if p in _adapters]
