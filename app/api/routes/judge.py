import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.schemas import JudgeResultOut
from app.models.db_models import Conversation, DebateRound, JudgeResult, AIModel

router = APIRouter(prefix="/judge", tags=["judge"])


@router.get("/{conversation_id}", response_model=JudgeResultOut)
async def get_judge_result(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(JudgeResult)
        .where(JudgeResult.conversation_id == uuid.UUID(conversation_id))
    )
    jr = result.scalar_one_or_none()
    if not jr:
        raise HTTPException(status_code=404, detail="Judge result not found")

    winner_provider = None
    winner_display = None
    if jr.winner_model_id:
        model = await db.get(AIModel, jr.winner_model_id)
        if model:
            winner_provider = model.provider
            winner_display = model.display_name

    return {
        "id": jr.id,
        "conversation_id": jr.conversation_id,
        "winner_provider": winner_provider,
        "winner_display_name": winner_display,
        "scores": jr.scores,
        "summary": jr.summary,
        "created_at": jr.created_at,
    }
