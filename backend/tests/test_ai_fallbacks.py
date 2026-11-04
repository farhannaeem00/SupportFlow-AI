import json
from uuid import uuid4

from app.services.ai.analysis_service import ConversationAnalysisService
from app.services.ai.reply_service import ConversationReplyService


class FailingProvider:
    def generate_response(self, system_prompt, user_prompt):
        raise RuntimeError("Simulated Groq API failure")


class SequenceProvider:
    def __init__(self, responses):
        self.responses = iter(responses)

    def generate_response(self, system_prompt, user_prompt):
        response = next(self.responses)

        if isinstance(response, Exception):
            raise response

        return response


def valid_knowledge_result():
    return {
        "text": "Customers can request a refund within 30 days.",
        "metadata": {
            "filename": "refund-policy.txt",
            "document_id": str(uuid4()),
            "chunk_index": 0,
        },
    }


def test_analysis_uses_conservative_fallback_when_provider_fails():
    service = ConversationAnalysisService(FailingProvider())

    result = service.analyze(
        message="I need help with my account."
    )

    assert result.intent == "general_support"
    assert result.sentiment == "neutral"
    assert result.priority == "normal"
    assert result.confidence == 0.0
    assert result.requires_human is True


def test_analysis_uses_fallback_for_invalid_json():
    service = ConversationAnalysisService(
        SequenceProvider(["This is not valid JSON"])
    )

    result = service.analyze(message="I need help.")

    assert result.confidence == 0.0
    assert result.requires_human is True


def test_standard_reply_uses_fallback_when_provider_fails():
    service = ConversationReplyService(FailingProvider())

    result = service.generate_reply(
        message="Where is my order?"
    )

    assert result.response == (
        "Thank you for contacting our support team. "
        "We've received your message. A support agent "
        "will review your request and assist you."
    )


def test_knowledge_reply_uses_fallback_when_generation_fails():
    service = ConversationReplyService(FailingProvider())

    result = service.generate_knowledge_reply(
        message="What is your refund policy?",
        knowledge_results=[valid_knowledge_result()],
    )

    assert result.response == service.GENERATION_FAILURE_RESPONSE
    assert result.sources == []
    assert result.grounded is False
    assert result.requires_human is True


def test_knowledge_reply_rejects_answer_when_verification_fails():
    provider = SequenceProvider([
        "Customers can request a refund within 30 days.",
        RuntimeError("Verification API failure"),
    ])

    service = ConversationReplyService(provider)

    result = service.generate_knowledge_reply(
        message="What is your refund policy?",
        knowledge_results=[valid_knowledge_result()],
    )

    assert "couldn't verify an answer" in result.response.lower()
    assert result.sources == []
    assert result.grounded is False
    assert result.requires_human is True


def test_knowledge_reply_uses_no_knowledge_fallback_without_sources():
    service = ConversationReplyService(FailingProvider())

    result = service.generate_knowledge_reply(
        message="What is your refund policy?",
        knowledge_results=[],
    )

    assert result.response == service.NO_KNOWLEDGE_RESPONSE
    assert result.sources == []
    assert result.grounded is False
    assert result.requires_human is True