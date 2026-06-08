import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.schemas.schemas import AdminConversationOut
from app.models.db_models import (
    Conversation, DebateRound, JudgeResult, ConsensusResult, User
)
from app.api.routes.auth import get_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/debates", response_model=list[AdminConversationOut])
async def admin_list_debates(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.user))
        .order_by(Conversation.created_at.desc())
    )
    convs = result.scalars().all()

    round_counts: dict[str, int] = {}
    if convs:
        ids = [c.id for c in convs]
        rc_result = await db.execute(
            select(DebateRound.conversation_id, func.count(DebateRound.id))
            .where(DebateRound.conversation_id.in_(ids))
            .group_by(DebateRound.conversation_id)
        )
        round_counts = {str(row[0]): row[1] for row in rc_result.all()}

    return [
        AdminConversationOut(
            id=c.id,
            topic=c.topic,
            status=c.status,
            selected_models=c.selected_models,
            created_at=c.created_at,
            completed_at=c.completed_at,
            user_email=c.user.email if c.user else None,
            round_count=round_counts.get(str(c.id), 0),
        )
        for c in convs
    ]


@router.get("/stats")
async def admin_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(Conversation.id)))
    done = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.status == "done")
    )
    failed = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.status == "failed")
    )
    running = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.status == "running")
    )
    users = await db.scalar(select(func.count(User.id)))

    return {
        "total_debates": total or 0,
        "done": done or 0,
        "failed": failed or 0,
        "running": running or 0,
        "total_users": users or 0,
    }


@router.delete("/debates/{conversation_id}", status_code=204)
async def admin_delete_debate(
    conversation_id: str,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 토론 ID입니다.")

    conv = await db.get(Conversation, cid)
    if not conv:
        raise HTTPException(status_code=404, detail="토론을 찾을 수 없습니다.")

    # FK 제약 순서대로 삭제
    await db.execute(delete(DebateRound).where(DebateRound.conversation_id == cid))
    await db.execute(delete(JudgeResult).where(JudgeResult.conversation_id == cid))
    await db.execute(delete(ConsensusResult).where(ConsensusResult.conversation_id == cid))
    await db.delete(conv)
    await db.commit()

    # 인메모리 SSE 진행 상태 정리
    from app.api.routes.debate import _debate_progress
    _debate_progress.pop(conversation_id, None)
