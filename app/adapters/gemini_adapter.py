import time
from typing import AsyncGenerator
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
from app.adapters.base import BaseAIAdapter, AIResponse
from app.core.config import settings

# Gemini finish_reason 값 (SDK 버전마다 다를 수 있어 모두 커버)
_MAX_TOKENS_REASONS = {"MAX_TOKENS", "2", "FinishReason.MAX_TOKENS", 2}

# 안전 필터를 최소화해 긴 한국어 텍스트가 차단되는 상황 방지
_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}


def _extract_text(response) -> str:
    """candidates[0].content.parts 에서 텍스트를 명시적으로 추출.
    response.text 는 안전 필터 차단·candidates 없음 등의 경우 ValueError를 던지므로 직접 파싱."""
    try:
        if not response.candidates:
            return ""
        parts = response.candidates[0].content.parts
        return "".join(p.text for p in parts if hasattr(p, "text") and p.text)
    except Exception:
        # 최후 수단: SDK 기본 프로퍼티
        try:
            return response.text or ""
        except Exception:
            return ""


def _finish_reason(response) -> str:
    try:
        return str(response.candidates[0].finish_reason)
    except Exception:
        return ""


def _build_model(system_instruction: str | None, max_tokens: int) -> genai.GenerativeModel:
    config = GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=0.7,
    )
    kwargs: dict = {
        "model_name": settings.GEMINI_MODEL,
        "generation_config": config,
        "safety_settings": _SAFETY_SETTINGS,
    }
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    return genai.GenerativeModel(**kwargs)


def _to_contents(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """OpenAI 형식 messages → Gemini contents + system_instruction 분리."""
    system_parts: list[str] = []
    contents: list[dict] = []

    for msg in messages:
        role = msg["role"]
        text = msg["content"]
        if role == "system":
            system_parts.append(text)
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": text}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": text}]})

    system_instruction = "\n".join(system_parts) if system_parts else None
    return system_instruction, contents


class GeminiAdapter(BaseAIAdapter):
    provider = "gemini"
    display_name = "Gemini 2.5"

    def __init__(self):
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)

    async def generate(self, messages: list[dict], max_tokens: int = 1000) -> AIResponse:
        if not settings.GOOGLE_API_KEY:
            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content="[Google API key not configured]",
                tokens_used=0,
                latency_ms=0,
                error="API key missing",
            )

        start = time.time()
        try:
            system_instruction, contents = _to_contents(messages)
            model = _build_model(system_instruction, max_tokens)

            # chat API 대신 generate_content_async 직접 호출 — 더 안정적인 텍스트 추출
            response = await model.generate_content_async(contents)
            full_text = _extract_text(response)

            # 여전히 MAX_TOKENS로 잘린 경우 → 이어쓰기 1회
            if _finish_reason(response) in _MAX_TOKENS_REASONS and full_text:
                cont_contents = contents + [
                    {"role": "model", "parts": [{"text": full_text}]},
                    {"role": "user",  "parts": [{"text": "이어서 계속 작성해주세요."}]},
                ]
                cont_response = await model.generate_content_async(cont_contents)
                cont_text = _extract_text(cont_response)
                if cont_text:
                    full_text = full_text + cont_text

            latency = int((time.time() - start) * 1000)
            tokens_used = 0
            try:
                if response.usage_metadata:
                    tokens_used = response.usage_metadata.total_token_count or 0
            except Exception:
                pass

            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content=full_text,
                tokens_used=tokens_used,
                latency_ms=latency,
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return AIResponse(
                provider=self.provider,
                display_name=self.display_name,
                content=f"[Gemini error: {str(e)}]",
                tokens_used=0,
                latency_ms=latency,
                error=str(e),
            )

    async def stream(self, messages: list[dict], max_tokens: int = 1000) -> AsyncGenerator[str, None]:
        if not settings.GOOGLE_API_KEY:
            yield "[Google API key not configured]"
            return

        try:
            system_instruction, contents = _to_contents(messages)
            model = _build_model(system_instruction, max_tokens)
            response = await model.generate_content_async(contents, stream=True)

            async for chunk in response:
                try:
                    text = _extract_text(chunk)
                    if text:
                        yield text
                except Exception:
                    pass
        except Exception as e:
            yield f"[Gemini error: {str(e)}]"
