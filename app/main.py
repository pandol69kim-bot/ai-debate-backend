from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import engine, Base, AsyncSessionLocal
from app.api.routes import debate, models, judge, consensus, rankings, auth, admin
from app.models import db_models


app = FastAPI(
    title=settings.APP_NAME,
    description="AI 멀티 모델 경쟁·토론 플랫폼 API",
    version="1.0.0",
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