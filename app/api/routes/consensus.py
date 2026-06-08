import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.schemas import ConsensusResultOut
from app.models.db_models import ConsensusResult

router = APIRouter(prefix="/consensus", tags=["consensus"])


@router.get("/{conversation_id}", response_model=ConsensusResultOut)
async def get_consensus(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ConsensusResult)
        .where(ConsensusResult.conversation_id == uuid.UUID(conversation_id))
    )
    cr = result.scalar_one_or_none()
    if not cr:
        raise HTTPException(status_code=404, detail="Consensus result not found")
    return cr
