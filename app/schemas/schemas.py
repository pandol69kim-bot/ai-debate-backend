from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.db_models import ConversationStatus, RankingPeriod


# Auth
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    plan: str
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminConversationOut(BaseModel):
    id: UUID
    topic: str
    status: ConversationStatus
    selected_models: List[str]
    created_at: datetime
    completed_at: Optional[datetime] = None
    user_email: Optional[str] = None
    round_count: int = 0


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# AI Models
class AIModelOut(BaseModel):
    id: UUID
    provider: str
    model_name: str
    display_name: str
    is_active: bool
    api_key_configured: bool = True

    model_config = {"from_attributes": True}


# Debate
class DebateStartRequest(BaseModel):
    topic: str
    selected_models: List[str] = ["gpt", "claude", "gemini"]
    num_rounds: int = 3


class DebateStartResponse(BaseModel):
    conversation_id: UUID
    status: str


class DebateRoundOut(BaseModel):
    id: UUID
    round_no: int
    model_id: UUID
    provider: str
    display_name: str
    content: str
    latency_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: UUID
    topic: str
    status: ConversationStatus
    selected_models: List[str]
    created_at: datetime
    completed_at: Optional[datetime] = None
    debate_rounds: List[DebateRoundOut] = []

    model_config = {"from_attributes": True}


# Multi-query
class MultiQueryRequest(BaseModel):
    topic: str
    selected_models: List[str] = ["gpt", "claude", "gemini"]


class ModelResponse(BaseModel):
    provider: str
    display_name: str
    content: str
    latency_ms: int
    error: Optional[str] = None


class MultiQueryResponse(BaseModel):
    topic: str
    responses: List[ModelResponse]


# Judge
class JudgeEvaluateRequest(BaseModel):
    conversation_id: UUID


class ModelScore(BaseModel):
    provider: str
    display_name: str
    accuracy: float
    logic: float
    evidence: float
    creativity: float
    feasibility: float
    total: float


class JudgeResultOut(BaseModel):
    id: UUID
    conversation_id: UUID
    winner_provider: Optional[str] = None
    winner_display_name: Optional[str] = None
    scores: Dict[str, Any]
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


# Consensus
class ConsensusRequest(BaseModel):
    conversation_id: UUID


class ConsensusResultOut(BaseModel):
    id: UUID
    conversation_id: UUID
    final_answer: str
    confidence_score: float
    vote_distribution: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# Rankings
class RankingOut(BaseModel):
    rank: int
    model_id: UUID
    provider: str
    display_name: str
    period: RankingPeriod
    elo_score: float
    win_count: int
    loss_count: int
    total_debates: int
    win_rate: float
    avg_accuracy: float

    model_config = {"from_attributes": True}


# SSE Event
class SSEEvent(BaseModel):
    event: str
    data: Dict[str, Any]
