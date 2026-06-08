from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.schemas.schemas import RankingOut
from app.models.db_models import Ranking, RankingPeriod

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/", response_model=list[RankingOut])
async def get_rankings(
    period: RankingPeriod = Query(default=RankingPeriod.ALL_TIME),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ranking)
        .options(selectinload(Ranking.model))
        .where(Ranking.period == period)
        .order_by(Ranking.elo_score.desc())
    )
    rankings = result.scalars().all()

    return [
        {
            "rank": i + 1,
            "model_id": r.model_id,
            "provider": r.model.provider,
            "display_name": r.model.display_name,
            "period": r.period,
            "elo_score": r.elo_score,
            "win_count": r.win_count,
            "loss_count": r.loss_count,
            "total_debates": r.total_debates,
            "win_rate": r.win_count / r.total_debates if r.total_debates > 0 else 0.0,
            "avg_accuracy": r.avg_accuracy,
        }
        for i, r in enumerate(rankings)
    ]
