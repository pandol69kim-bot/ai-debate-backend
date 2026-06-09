import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine, Base, AsyncSessionLocal
from app.api.routes import debate, models, judge, consensus, rankings, auth, admin
from app.models import db_models



@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_models()
    yield

    await engine.dispose()


async def _seed_models():
    initial_models = [
        {"provider": "gpt", "model_name": "gpt-4o", "display_name": "GPT-4o"},
        {"provider": "claude", "model_name": "claude-opus-4-8", "display_name": "Claude Opus"},
        {"provider": "gemini", "model_name": "gemini-2.0-flash-exp", "display_name": "Gemini 2.0"},
    ]
    from sqlalchemy import select
    from app.models.db_models import AIModel

    async with AsyncSessionLocal() as db:
        for m in initial_models:
            result = await db.execute(select(AIModel).where(AIModel.provider == m["provider"]))
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(AIModel(id=uuid.uuid4(), **m))
        await db.commit()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI 멀티 모델 경쟁·토론 플랫폼 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(debate.router, prefix=settings.API_V1_STR)
app.include_router(models.router, prefix=settings.API_V1_STR)
app.include_router(judge.router, prefix=settings.API_V1_STR)
app.include_router(consensus.router, prefix=settings.API_V1_STR)
app.include_router(rankings.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}
