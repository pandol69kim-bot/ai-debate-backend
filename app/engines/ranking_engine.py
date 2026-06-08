import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.db_models import AIModel, Ranking, RankingPeriod
import uuid


K_FACTOR = 32


def calculate_elo(winner_elo: float, loser_elo: float) -> tuple[float, float]:
    expected_winner = 1 / (1 + math.pow(10, (loser_elo - winner_elo) / 400))
    expected_loser = 1 - expected_winner
    new_winner = winner_elo + K_FACTOR * (1 - expected_winner)
    new_loser = loser_elo + K_FACTOR * (0 - expected_loser)
    return round(new_winner, 2), round(new_loser, 2)


class RankingEngine:
    async def update_after_debate(
        self,
        db: AsyncSession,
        winner_provider: str,
        all_providers: list[str],
        avg_scores: dict[str, float],
        period: RankingPeriod = RankingPeriod.ALL_TIME,
    ) -> None:
        for provider in all_providers:
            await self._ensure_ranking(db, provider, period)

        loser_providers = [p for p in all_providers if p != winner_provider]

        for loser in loser_providers:
            winner_ranking = await self._get_ranking(db, winner_provider, period)
            loser_ranking = await self._get_ranking(db, loser, period)

            if winner_ranking and loser_ranking:
                new_winner_elo, new_loser_elo = calculate_elo(
                    winner_ranking.elo_score,
                    loser_ranking.elo_score,
                )
                winner_ranking.elo_score = new_winner_elo
                loser_ranking.elo_score = new_loser_elo

        for provider in all_providers:
            ranking = await self._get_ranking(db, provider, period)
            if ranking:
                ranking.total_debates += 1
                if provider == winner_provider:
                    ranking.win_count += 1
                else:
                    ranking.loss_count += 1
                if provider in avg_scores:
                    n = ranking.total_debates
                    ranking.avg_accuracy = (ranking.avg_accuracy * (n - 1) + avg_scores[provider]) / n
                ranking.updated_at = datetime.utcnow()

        await db.commit()

    async def _ensure_ranking(self, db: AsyncSession, provider: str, period: RankingPeriod) -> None:
        ranking = await self._get_ranking(db, provider, period)
        if not ranking:
            model = await self._get_model_by_provider(db, provider)
            if model:
                new_ranking = Ranking(
                    id=uuid.uuid4(),
                    model_id=model.id,
                    period=period,
                    elo_score=1200.0,
                )
                db.add(new_ranking)
                await db.flush()

    async def _get_ranking(self, db: AsyncSession, provider: str, period: RankingPeriod) -> Ranking | None:
        model = await self._get_model_by_provider(db, provider)
        if not model:
            return None
        result = await db.execute(
            select(Ranking).where(
                Ranking.model_id == model.id,
                Ranking.period == period,
            )
        )
        return result.scalar_one_or_none()

    async def _get_model_by_provider(self, db: AsyncSession, provider: str) -> AIModel | None:
        result = await db.execute(
            select(AIModel).where(AIModel.provider == provider, AIModel.is_active == True)
        )
        return result.scalar_one_or_none()


ranking_engine = RankingEngine()
