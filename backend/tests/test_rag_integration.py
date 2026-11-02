
from uuid import uuid4

import pytest

from app.models.conversation import Conversation
from app.models.conversation_ai_insight import ConversationAIInsight
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message
from app.models.organization_ai_settings import OrganizationAISettings

from app.schemas.ai import (
    AIReply,
    ConversationAnalysis,
    KnowledgeAIReply,
    KnowledgeSource,
)

from app.services.ai.conversation_ai_service import ConversationAIService

from tests.test_conversations import (
    auth_headers,
    create_test_customer,
    create_test_conversation,
    register_owner,
)


def create_conversation_with_customer_message(
    client,
    db_session,
    owner,
):
    customer = create_test_customer(client, owner)

    response = create_test_conversation(
        client,
        owner,
        customer["id"],
    )

    assert response.status_code == 201

    conversation_id = response.json()["id"]

    conversation = db_session.get(
        Conversation,
        __import__("uuid").UUID(conversation_id),
    )

    message = Message(
        conversation_id=conversation.id,
        sender_type="customer",
        sender_customer_id=__import__("uuid").UUID(customer["id"]),
        content="How can I reset my account password?",
    )

    db_session.add(message)
    db_session.commit()

    return conversation


def configure_ai_services(service):
    service.analysis_service.analyze = lambda **kwargs: ConversationAnalysis(
        intent="account_support",
        sentiment="neutral",
        priority="normal",
        confidence=0.95,
        requires_human=False,
        reasoning="Customer needs account assistance.",
    )


def test_rag_reply_sources_are_saved_with_ai_insight(
    client,
    db_session,
    monkeypatch,
):
    owner = register_owner(client, "rag_sources@example.com")

    conversation = create_conversation_with_customer_message(
        client,
        db_session,
        owner,
    )

    knowledge_base = KnowledgeBase(
        organization_id=conversation.organization_id,
        name="Account Help",
        description="Account support documentation",
        is_active=True,
    )

    db_session.add(knowledge_base)
    db_session.commit()

    source_id = uuid4()

    service = ConversationAIService()
    configure_ai_services(service)

    monkeypatch.setattr(
        "app.services.ai.conversation_ai_service.retrieve_knowledge",
        lambda **kwargs: [
            {
                "text": "Users can reset their password from account settings.",
                "source": "account-guide.txt",
                "document_id": source_id,
                "chunk_index": 0,
                "distance": 0.15,
            }
        ],
    )

    service.reply_service.generate_knowledge_reply = (
        lambda **kwargs: KnowledgeAIReply(
            response="Open account settings and select Reset Password.",
            sources=[
                KnowledgeSource(
                    document_id=source_id,
                    filename="account-guide.txt",
                    chunk_index=0,
                )
            ],
            grounded=True,
            requires_human=False,
        )
    )

    insight = service.process_conversation(
        db=db_session,
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
    )

    assert insight.suggested_reply == (
        "Open account settings and select Reset Password."
    )

    assert len(insight.suggested_reply_sources) == 1

    assert insight.suggested_reply_sources[0]["document_id"] == str(
        source_id
    )

    assert insight.suggested_reply_sources[0]["filename"] == (
        "account-guide.txt"
    )

    assert insight.requires_human is False


def test_rag_without_relevant_knowledge_requires_human(
    client,
    db_session,
    monkeypatch,
):
    owner = register_owner(client, "rag_escalation@example.com")

    conversation = create_conversation_with_customer_message(
        client,
        db_session,
        owner,
    )

    knowledge_base = KnowledgeBase(
        organization_id=conversation.organization_id,
        name="Empty Knowledge Base",
        is_active=True,
    )

    db_session.add(knowledge_base)
    db_session.commit()

    service = ConversationAIService()
    configure_ai_services(service)

    monkeypatch.setattr(
        "app.services.ai.conversation_ai_service.retrieve_knowledge",
        lambda **kwargs: [],
    )

    service.reply_service.generate_knowledge_reply = (
        lambda **kwargs: KnowledgeAIReply(
            response=(
                "I could not find this information in the "
                "available support documentation. "
                "Please contact a support agent."
            ),
            sources=[],
            grounded=False,
            requires_human=True,
        )
    )

    insight = service.process_conversation(
        db=db_session,
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
    )

    assert insight.requires_human is True
    assert insight.suggested_reply_sources == []
    assert insight.priority == "high"


def test_ai_disabled_prevents_new_ai_processing(
    client,
    db_session,
    monkeypatch,
):
    owner = register_owner(client, "rag_disabled@example.com")

    conversation = create_conversation_with_customer_message(
        client,
        db_session,
        owner,
    )

    settings = OrganizationAISettings(
        organization_id=conversation.organization_id,
        ai_enabled=False,
        suggestions_enabled=True,
    )

    db_session.add(settings)
    db_session.commit()

    service = ConversationAIService()

    def unexpected_analysis(**kwargs):
        pytest.fail("Analysis must not run when AI is disabled.")

    monkeypatch.setattr(
        service.analysis_service,
        "analyze",
        unexpected_analysis,
    )

    with pytest.raises(
        ValueError,
        match="AI processing is disabled",
    ):
        service.process_conversation(
            db=db_session,
            organization_id=conversation.organization_id,
            conversation_id=conversation.id,
        )


def test_suggestions_disabled_skips_knowledge_retrieval(
    client,
    db_session,
    monkeypatch,
):
    owner = register_owner(client, "rag_suggestions_off@example.com")

    conversation = create_conversation_with_customer_message(
        client,
        db_session,
        owner,
    )

    settings = OrganizationAISettings(
        organization_id=conversation.organization_id,
        ai_enabled=True,
        suggestions_enabled=False,
    )

    db_session.add(settings)
    db_session.commit()

    service = ConversationAIService()
    configure_ai_services(service)

    def unexpected_retrieval(**kwargs):
        pytest.fail("Knowledge retrieval must be skipped.")

    monkeypatch.setattr(
        "app.services.ai.conversation_ai_service.retrieve_knowledge",
        unexpected_retrieval,
    )

    insight = service.process_conversation(
        db=db_session,
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
    )

    assert insight.suggested_reply is None
    assert insight.suggested_reply_sources == []


def test_organization_without_knowledge_base_uses_legacy_reply(
    client,
    db_session,
    monkeypatch,
):
    owner = register_owner(client, "rag_legacy@example.com")

    conversation = create_conversation_with_customer_message(
        client,
        db_session,
        owner,
    )

    service = ConversationAIService()
    configure_ai_services(service)

    service.reply_service.generate_reply = (
        lambda **kwargs: AIReply(
            response="Please use the password reset option."
        )
    )

    def unexpected_retrieval(**kwargs):
        pytest.fail(
            "Retrieval should not run when no active knowledge base exists."
        )

    monkeypatch.setattr(
        "app.services.ai.conversation_ai_service.retrieve_knowledge",
        unexpected_retrieval,
    )

    insight = service.process_conversation(
        db=db_session,
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
    )

    assert insight.suggested_reply == (
        "Please use the password reset option."
    )

    assert insight.suggested_reply_sources == []
