
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.conversation_ai_insight import ConversationAIInsight
from app.schemas.ai import ConversationAnalysis
from app.services.ai.analysis_service import ConversationAnalysisService
from app.services.ai.reply_service import ConversationReplyService
from app.services.ai.groq_provider import GroqProvider
from app.models.conversation_event import ConversationEvent

logger = logging.getLogger(__name__)


class ConversationAIService:
    """Coordinates AI analysis and suggested replies for conversations."""

    def __init__(self, provider: GroqProvider | None = None):
        shared_provider = provider or GroqProvider()

        self.analysis_service = ConversationAnalysisService(shared_provider)
        self.reply_service = ConversationReplyService(shared_provider)

    def process_conversation(
        self,
        db: Session,
        organization_id: UUID,
        conversation_id: UUID,
    ) -> ConversationAIInsight:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.organization_id == organization_id,
            )
        )

        if conversation is None:
            raise LookupError("Conversation not found.")

        messages = list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            ).all()
        )

        if not messages:
            raise ValueError("Cannot analyze a conversation without messages.")

        latest_message = messages[-1]

        if latest_message.sender_type != "customer":
            raise ValueError("The latest conversation message must be from a customer.")

        context = "\n".join(
            f"{message.sender_type}: {message.content}"
            for message in messages[-20:]
        )

        # Analyze the latest customer message.
        analysis: ConversationAnalysis = self.analysis_service.analyze(
            message=latest_message.content,
            conversation_context=context,
        )

        # Generate a suggested response for the support agent.
        # This is NOT automatically sent to the customer.
        suggested_reply = self.reply_service.generate_reply(
            message=latest_message.content,
            conversation_context=context,
        )

        insight = db.scalar(
            select(ConversationAIInsight).where(
                ConversationAIInsight.conversation_id == conversation_id,
                ConversationAIInsight.organization_id == organization_id,
            )
        )

        if insight is None:
            insight = ConversationAIInsight(
                organization_id=organization_id,
                conversation_id=conversation_id,
            )
            db.add(insight)

        insight.intent = analysis.intent
        insight.sentiment = analysis.sentiment
        insight.priority = analysis.priority
        insight.confidence = analysis.confidence
        insight.requires_human = analysis.requires_human
        insight.reasoning = analysis.reasoning
        insight.suggested_reply = suggested_reply.response

        # A newly generated suggestion requires a fresh agent review.
        insight.suggestion_status = "pending"
        insight.reviewed_by_id = None
        insight.reviewed_at = None

        # Keep the conversation priority synchronized with the analysis.
        # Apply a minimum high priority when human intervention is required.
        priority_order = {
            "low": 1,
            "normal": 2,
            "high": 3,
            "urgent": 4,
        }

        old_priority = conversation.priority
        new_priority = analysis.priority

        if analysis.requires_human and priority_order[new_priority] < priority_order["high"]:
            new_priority = "high"

        conversation.priority = new_priority

        # Record AI escalation in the conversation audit history.
        if analysis.requires_human:
            db.add(
                ConversationEvent(
                    conversation_id=conversation.id,
                    actor_id=None,  # AI-generated system event
                    event_type="ai_escalated",
                    old_value=old_priority,
                    new_value=(
                        f"{new_priority}: {analysis.reasoning}"
                    ),
                )
            )
        try:
            db.commit()
            db.refresh(insight)
        except Exception:
            db.rollback()
            logger.exception("Failed to save conversation AI insights.")
            raise

        return insight
