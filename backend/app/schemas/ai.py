
from typing import Literal

from pydantic import BaseModel, Field

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict



class ConversationAnalysis(BaseModel):
    intent: str = Field(min_length=1, max_length=100)
    sentiment: Literal["positive", "neutral", "negative"]
    priority: Literal["low", "normal", "high", "urgent"]
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human: bool
    reasoning: str = Field(min_length=1, max_length=500)


class AIReply(BaseModel):
    response: str = Field(min_length=1, max_length=4000)




class ConversationAIInsightResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    intent: str
    sentiment: str
    priority: str
    confidence: float
    requires_human: bool
    reasoning: str
    suggested_reply: str | None
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)




class AISuggestionReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]


class AISuggestionReviewResponse(BaseModel):
    conversation_id: UUID
    suggestion_status: Literal["pending", "approved", "rejected"]
    reviewed_by_id: UUID | None
    reviewed_at: datetime



class AIEscalationQueueItem(BaseModel):
    conversation_id: UUID
    subject: str
    status: str
    priority: str
    assigned_to_id: UUID | None
    intent: str
    sentiment: str
    confidence: float
    reasoning: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AIAnalyticsDistribution(BaseModel):
    name: str
    count: int


class AIAnalyticsResponse(BaseModel):
    total_analyzed: int
    escalated_count: int
    average_confidence: float
    pending_suggestions: int
    approved_suggestions: int
    rejected_suggestions: int
    intent_distribution: list[AIAnalyticsDistribution]
    sentiment_distribution: list[AIAnalyticsDistribution]
