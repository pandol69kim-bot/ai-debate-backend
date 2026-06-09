from fastapi import FastAPI

app = FastAPI(
    title="AI Arena",
    description="AI 멀티 모델 경쟁·토론 플랫폼 API",
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "AI Arena"}


@app.get("/")
async def root():
    return {"message": "AI Arena API"}