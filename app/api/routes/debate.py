import uuid
import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from app.db.session import get_db
from app.schemas.schemas import DebateStartRequest, DebateStartResponse, ConversationOut
from app.models.db_models import Conversation, DebateRound, AIModel, ConversationStatus, JudgeResult, ConsensusResult
from app.engines.debate_engine import debate_engine
from app.engines.judge_engine import judge_engine
from app.engines.consensus_engine import consensus_engine
from app.engines.ranking_engine import ranking_engine
from app.models.db_models import RankingPeriod
from app.api.routes.auth import _get_user_from_token

router = APIRouter(prefix="/debate", tags=["debate"])

_debate_progress: dict[str, list] = {}


async def _run_debate_background(conversation_id: str, topic: str, providers: list[str], num_rounds: int):
    from app.db.session import AsyncSessionLocal

    _debate_progress[conversation_id] = []

    async with AsyncSessionLocal() as db:
        try:
            conv = await db.get(Conversation, uuid.UUID(conversation_id))
            if not conv:
                return
            conv.status = ConversationStatus.RUNNING
            await db.commit()

            # Map providers to AIModel ids
            model_map: dict[str, AIModel] = {}
            for provider in providers:
                result = await db.execute(
                    select(AIModel).where(AIModel.provider == provider, AIModel.is_active == True)
                )
                model = result.scalar_one_or_none()
                if model:
                    model_map[provider] = model

            # Run debate rounds
            previous_responses: dict[str, str] = {}
            for round_no in range(1, num_rounds + 1):
                if round_no == 1:
                    responses = await debate_engine.run_initial_round(topic, providers)
                else:
                    responses = await debate_engine.run_debate_round(topic, round_no, providers, previous_responses)

                previous_responses = {}
                for resp in responses:
                    model = model_map.get(resp.provider)
                    if not model:
                        continue
                    dr = DebateRound(
                        id=uuid.uuid4(),
                        conversation_id=conv.id,
                        round_no=round_no,
                        model_id=model.id,
                        content=resp.content,
                        tokens_used=resp.tokens_used,
                        latency_ms=resp.latency_ms,
                    )
                    db.add(dr)
                    previous_responses[resp.provider] = resp.content

                    event = {
                        "type": "round_response",
                        "round_no": round_no,
                        "provider": resp.provider,
                        "display_name": resp.display_name,
                        "content": resp.content,
                        "latency_ms": resp.latency_ms,
                    }
                    _debate_progress[conversation_id].append(event)

                await db.commit()

                event = {"type": "round_complete", "round_no": round_no}
                _debate_progress[conversation_id].append(event)

            # Judge evaluation
            conv.status = ConversationStatus.JUDGING
            await db.commit()

            all_rounds_data = [
                {
                    "provider": m_map_entry,
                    "display_name": next(
                        (v.display_name for k, v in model_map.items() if k == m_map_entry), m_map_entry
                    ),
                    "round_no": rn,
                    "content": content,
                }
                for m_map_entry, content in previous_responses.items()
                for rn in [num_rounds]
            ]

            result = await db.execute(
                select(DebateRound)
                .where(DebateRound.conversation_id == conv.id)
                .order_by(DebateRound.round_no)
            )
            all_drs = result.scalars().all()
            full_rounds_data = [
                {
                    "provider": model_map[next(k for k, v in model_map.items() if v.id == dr.model_id)].provider
                    if any(v.id == dr.model_id for v in model_map.values()) else "unknown",
                    "display_name": next(
                        (v.display_name for v in model_map.values() if v.id == dr.model_id), "unknown"
                    ),
                    "round_no": dr.round_no,
                    "content": dr.content,
                }
                for dr in all_drs
            ]

            judge_result = await judge_engine.evaluate(topic, full_rounds_data)

            winner_provider = judge_result.get("winner")
            winner_model = model_map.get(winner_provider) if winner_provider else None

            jr = JudgeResult(
                id=uuid.uuid4(),
                conversation_id=conv.id,
                winner_model_id=winner_model.id if winner_model else None,
                scores=judge_result.get("scores", {}),
                summary=judge_result.get("summary", ""),
            )
            db.add(jr)
            await db.commit()

            _debate_progress[conversation_id].append({
                "type": "judge_complete",
                "winner": winner_provider,
                "scores": judge_result.get("scores", {}),
                "summary": judge_result.get("summary", ""),
            })

            # Consensus
            final_responses = [
                {"provider": p, "display_name": m.display_name, "content": previous_responses.get(p, "")}
                for p, m in model_map.items()
                if p in previous_responses
            ]
            consensus = await consensus_engine.generate(topic, final_responses)

            cr = ConsensusResult(
                id=uuid.uuid4(),
                conversation_id=conv.id,
                final_answer=consensus["final_answer"],
                confidence_score=consensus["confidence_score"],
                vote_distribution=consensus["vote_distribution"],
            )
            db.add(cr)

            # Update rankings
            if winner_provider:
                scores_map = {
                    p: judge_result.get("scores", {}).get(p, {}).get("total", 0) / 50.0
                    for p in providers
                }
                await ranking_engine.update_after_debate(
                    db, winner_provider, providers, scores_map, RankingPeriod.ALL_TIME
                )

            conv.status = ConversationStatus.DONE
            conv.completed_at = datetime.utcnow()
            await db.commit()

            _debate_progress[conversation_id].append({
                "type": "consensus_complete",
                "final_answer": consensus["final_answer"],
                "confidence_score": consensus["confidence_score"],
            })
            _debate_progress[conversation_id].append({"type": "done"})

        except Exception as e:
            async with AsyncSessionLocal() as db2:
                conv2 = await db2.get(Conversation, uuid.UUID(conversation_id))
                if conv2:
                    conv2.status = ConversationStatus.FAILED
                    await db2.commit()
            _debate_progress[conversation_id].append({"type": "error", "message": str(e)})


@router.get("/", response_model=list[ConversationOut])
async def list_debates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.debate_rounds).selectinload(DebateRound.model))
        .order_by(Conversation.created_at.desc())
        .limit(50)
    )
    convs = result.scalars().all()
    output = []
    for conv in convs:
        rounds_out = []
        for dr in conv.debate_rounds:
            rounds_out.append({
                "id": dr.id,
                "round_no": dr.round_no,
                "model_id": dr.model_id,
                "provider": dr.model.provider,
                "display_name": dr.model.display_name,
                "content": dr.content,
                "latency_ms": dr.latency_ms,
                "created_at": dr.created_at,
            })
        output.append({
            "id": conv.id,
            "topic": conv.topic,
            "status": conv.status,
            "selected_models": conv.selected_models,
            "created_at": conv.created_at,
            "completed_at": conv.completed_at,
            "debate_rounds": rounds_out,
        })
    return output


@router.post("/start", response_model=DebateStartResponse)
async def start_debate(
    body: DebateStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    await _get_user_from_token(authorization, db)

    conv = Conversation(
        id=uuid.uuid4(),
        topic=body.topic,
        selected_models=body.selected_models,
        status=ConversationStatus.PENDING,
    )
    db.add(conv)
    await db.commit()

    background_tasks.add_task(
        _run_debate_background,
        str(conv.id),
        body.topic,
        body.selected_models,
        body.num_rounds,
    )

    return DebateStartResponse(conversation_id=conv.id, status="pending")


@router.get("/{conversation_id}/stream")
async def stream_debate(conversation_id: str):
    async def event_generator():
        sent = 0
        max_wait = 300  # 5 minutes
        waited = 0

        yield f"data: {json.dumps({'type': 'connected', 'conversation_id': conversation_id})}\n\n"

        while waited < max_wait:
            progress = _debate_progress.get(conversation_id, [])
            while sent < len(progress):
                event = progress[sent]
                yield f"data: {json.dumps(event)}\n\n"
                sent += 1
                if event.get("type") in ("done", "error"):
                    return

            await asyncio.sleep(0.5)
            waited += 0.5

        yield f"data: {json.dumps({'type': 'timeout'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.debate_rounds).selectinload(DebateRound.model))
        .where(Conversation.id == uuid.UUID(conversation_id))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    rounds_out = []
    for dr in conv.debate_rounds:
        rounds_out.append({
            "id": dr.id,
            "round_no": dr.round_no,
            "model_id": dr.model_id,
            "provider": dr.model.provider,
            "display_name": dr.model.display_name,
            "content": dr.content,
            "latency_ms": dr.latency_ms,
            "created_at": dr.created_at,
        })

    return {
        "id": conv.id,
        "topic": conv.topic,
        "status": conv.status,
        "selected_models": conv.selected_models,
        "created_at": conv.created_at,
        "completed_at": conv.completed_at,
        "debate_rounds": rounds_out,
    }
