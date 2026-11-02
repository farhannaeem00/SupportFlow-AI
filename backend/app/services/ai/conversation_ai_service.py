
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.conversation_ai_insight import ConversationAIInsight
from app.models.conversation_event import ConversationEvent
from app.models.organization_ai_settings import OrganizationAISettings
from app.models.knowledge_base import KnowledgeBase

from app.schemas.ai import ConversationAnalysis
from app.services.ai.analysis_service import ConversationAnalysisService
from app.services.ai.reply_service import ConversationReplyService
from app.services.ai.groq_provider import GroqProvider
from app.services.organization_ai_settings_service import (
    get_or_create_ai_settings,
)
from app.services.knowledge.retrieval_service import retrieve_knowledge

logger = logging.getLogger(__name__)


class ConversationAIService:
    """Coordinates conversation analysis and knowledge-grounded suggestions."""

    PRIORITY_ORDER = {
        "low": 1,
        "normal": 2,
        "high": 3,
        "urgent": 4,
    }

    PRIORITY_BY_LEVEL = {
        1: "low",
        2: "normal",
        3: "high",
        4: "urgent",
    }

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

        # Load organization-specific AI settings.
        settings = get_or_create_ai_settings(db, organization_id)

        if not settings.ai_enabled:
            existing_insight = db.scalar(
                select(ConversationAIInsight).where(
                    ConversationAIInsight.conversation_id == conversation_id,
                    ConversationAIInsight.organization_id == organization_id,
                )
            )

            if existing_insight is not None:
                return existing_insight

            raise ValueError("AI processing is disabled for this organization.")

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
            raise ValueError(
                "The latest conversation message must be from a customer."
            )

        # Use the organization's configured context limit.
        context_messages = messages[-settings.max_context_messages:]

        context = "\n".join(
            f"{message.sender_type}: {message.content}"
            for message in context_messages
        )

        # Analyze the latest customer message.
        analysis: ConversationAnalysis = self.analysis_service.analyze(
            message=latest_message.content,
            conversation_context=context,
        )

        # Apply the organization's confidence threshold.
        low_confidence = (
            analysis.confidence < settings.confidence_threshold
        )

        requires_human = analysis.requires_human or low_confidence

        # Determine the minimum priority configured for escalation.
        effective_priority = analysis.priority

        if requires_human:
            minimum_priority = self.PRIORITY_BY_LEVEL[
                settings.escalation_priority_level
            ]

            if (
                self.PRIORITY_ORDER[effective_priority]
                < self.PRIORITY_ORDER[minimum_priority]
            ):
                effective_priority = minimum_priority

        suggested_reply = None
        suggested_reply_sources = []
        rag_requires_human = False

        if settings.suggestions_enabled:
            active_knowledge_bases = list(
                db.scalars(
                    select(KnowledgeBase).where(
                        KnowledgeBase.organization_id == organization_id,
                        KnowledgeBase.is_active.is_(True),
                    )
                ).all()
            )

            if active_knowledge_bases:
                # Search each active Knowledge Base within this organization.
                retrieved_results = []

                for knowledge_base in active_knowledge_bases:
                    results = retrieve_knowledge(
                        db=db,
                        organization_id=organization_id,
                        knowledge_base_id=knowledge_base.id,
                        query=latest_message.content,
                        limit=5,
                    )

                    retrieved_results.extend(results)

                # Combine results and keep the closest matches.
                retrieved_results.sort(
                    key=lambda item: item.get("distance", float("inf"))
                )

                retrieved_results = retrieved_results[:5]

                # Convert retrieval results into the format expected by
                # ConversationReplyService.
                formatted_results = [
                    {
                        "text": item["text"],
                        "metadata": {
                            "filename": item["source"],
                            "document_id": str(item["document_id"]),
                            "chunk_index": item["chunk_index"],
                        },
                        "distance": item.get("distance"),
                    }
                    for item in retrieved_results
                ]

                knowledge_reply = self.reply_service.generate_knowledge_reply(
                    message=latest_message.content,
                    knowledge_results=formatted_results,
                    conversation_context=context,
                )

                suggested_reply = knowledge_reply.response

                suggested_reply_sources = [
                    source.model_dump(mode="json")
                    for source in knowledge_reply.sources
                ]

                rag_requires_human = knowledge_reply.requires_human

            else:
                # Preserve the existing behavior for organizations that
                # have not uploaded any Knowledge Base documents.
                legacy_reply = self.reply_service.generate_reply(
                    message=latest_message.content,
                    conversation_context=context,
                )

                suggested_reply = legacy_reply.response

        requires_human = requires_human or rag_requires_human

        # Recalculate priority if RAG requires human intervention.
        if requires_human:
            minimum_priority = self.PRIORITY_BY_LEVEL[
                settings.escalation_priority_level
            ]

            if (
                self.PRIORITY_ORDER[effective_priority]
                < self.PRIORITY_ORDER[minimum_priority]
            ):
                effective_priority = minimum_priority

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
        insight.priority = effective_priority
        insight.confidence = analysis.confidence
        insight.requires_human = requires_human
        insight.reasoning = analysis.reasoning
        insight.suggested_reply = suggested_reply
        insight.suggested_reply_sources = suggested_reply_sources

        # A new suggestion requires a fresh agent review.
        insight.suggestion_status = "pending"
        insight.reviewed_by_id = None
        insight.reviewed_at = None

        old_priority = conversation.priority
        conversation.priority = effective_priority

        # Record AI escalation in the conversation audit history.
        if requires_human:
            db.add(
                ConversationEvent(
                    conversation_id=conversation.id,
                    actor_id=None,
                    event_type="ai_escalated",
                    old_value=old_priority,
                    new_value=f"{effective_priority}: {analysis.reasoning}",
                )
            )

        try:
            db.commit()
            db.refresh(insight)

        except Exception:
            db.rollback()
            logger.exception(
                "Failed to save conversation AI insights."
            )
            raise

        return insight
