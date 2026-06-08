import asyncio
import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.schemas import MultiQueryRequest, MultiQueryResponse, ModelResponse, AIModelOut
from app.adapters.registry import get_adapters_by_providers
from app.models.db_models import AIModel
from app.core.config import settings

router = APIRouter(prefix="/models", tags=["models"])

_API_KEY_MAP: dict[str, str] = {
    "gpt": settings.OPENAI_API_KEY,
    "claude": settings.ANTHROPIC_API_KEY,
    "gemini": settings.GOOGLE_API_KEY,
}


@router.get("/", response_model=list[AIModelOut])
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIModel).where(AIModel.is_active == True))
    models = result.scalars().all()
    return [
        AIModelOut(
            id=m.id,
            provider=m.provider,
            model_name=m.model_name,
            display_name=m.display_name,
            is_active=m.is_active,
            api_key_configured=bool(_API_KEY_MAP.get(m.provider, "")),
        )
        for m in models
    ]


@router.post("/query", response_model=MultiQueryResponse)
async def multi_query(body: MultiQueryRequest):
    adapters = get_adapters_by_providers(body.selected_models)

    messages = [
        {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다. 명확하고 간결하게 답변하세요."},
        {"role": "user", "content": body.topic},
    ]

    tasks = [adapter.generate(messages, max_tokens=600) for adapter in adapters]
    responses = await asyncio.gather(*tasks)

    return MultiQueryResponse(
        topic=body.topic,
        responses=[
            ModelResponse(
                provider=r.provider,
                display_name=r.display_name,
                content=r.content,
                latency_ms=r.latency_ms,
                error=r.error,
            )
            for r in responses
        ],
    )
