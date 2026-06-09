import sys
import traceback

print("=" * 50)
print("Starting application initialization...")
print("=" * 50)

try:
    print("[1/5] Importing FastAPI...")
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    print("✓ FastAPI imported")
except Exception as e:
    print(f"✗ Failed to import FastAPI: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[2/5] Importing settings...")
    from app.core.config import settings
    print(f"✓ Settings imported: {settings.APP_NAME}")
except Exception as e:
    print(f"✗ Failed to import settings: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[3/5] Importing database session...")
    from app.db.session import engine, Base, AsyncSessionLocal
    print("✓ Database session imported")
except Exception as e:
    print(f"✗ Failed to import database session: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[4/5] Importing database models...")
    from app.models import db_models
    print("✓ Database models imported")
except Exception as e:
    print(f"✗ Failed to import database models: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("[5/5] Importing routers...")
    from app.api.routes import debate, models, judge, consensus, rankings, auth, admin
    print("✓ All routers imported")
except Exception as e:
    print(f"✗ Failed to import routers: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=" * 50)
print("Creating FastAPI app...")
print("=" * 50)

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

print("Adding routers...")
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(debate.router, prefix=settings.API_V1_STR)
app.include_router(models.router, prefix=settings.API_V1_STR)
app.include_router(judge.router, prefix=settings.API_V1_STR)
app.include_router(consensus.router, prefix=settings.API_V1_STR)
app.include_router(rankings.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
print("✓ All routers added")

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}

print("=" * 50)
print("✓ Application initialized successfully!")
print("=" * 50)