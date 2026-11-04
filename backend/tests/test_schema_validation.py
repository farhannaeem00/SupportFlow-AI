
import pytest
from pydantic import ValidationError

from app.schemas.customer import CustomerUpdate
from app.schemas.conversation import ConversationCreate, MessageCreate
from app.schemas.team import InviteMemberRequest
from app.schemas.widget import (
    WidgetConversationCreate,
    WidgetMessageCreate,
)


def test_customer_update_rejects_null_full_name():
    with pytest.raises(ValidationError):
        CustomerUpdate(full_name=None)


def test_customer_update_rejects_whitespace_full_name():
    with pytest.raises(ValidationError):
        CustomerUpdate(full_name="   ")


def test_customer_update_trims_full_name():
    result = CustomerUpdate(full_name="  John Smith  ")
    assert result.full_name == "John Smith"


def test_conversation_create_trims_subject():
    result = ConversationCreate(
        customer_id="00000000-0000-0000-0000-000000000001",
        subject="  Support request  ",
    )
    assert result.subject == "Support request"


def test_conversation_create_rejects_whitespace_subject():
    with pytest.raises(ValidationError):
        ConversationCreate(
            customer_id="00000000-0000-0000-0000-000000000001",
            subject="   ",
        )


def test_message_create_rejects_whitespace_content():
    with pytest.raises(ValidationError):
        MessageCreate(content="   ")


def test_team_invite_rejects_whitespace_name():
    with pytest.raises(ValidationError):
        InviteMemberRequest(
            email="agent@example.com",
            full_name="   ",
            password="SecurePassword123",
        )


def test_team_invite_rejects_whitespace_password():
    with pytest.raises(ValidationError):
        InviteMemberRequest(
            email="agent@example.com",
            full_name="Test Agent",
            password="        ",
        )


def test_widget_conversation_trims_text_fields():
    result = WidgetConversationCreate(
        full_name="  John Smith  ",
        subject="  Need help  ",
        message="  My order is delayed  ",
    )

    assert result.full_name == "John Smith"
    assert result.subject == "Need help"
    assert result.message == "My order is delayed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("full_name", "   "),
        ("subject", "   "),
        ("message", "   "),
    ],
)
def test_widget_conversation_rejects_whitespace_fields(field, value):
    with pytest.raises(ValidationError):
        WidgetConversationCreate(**{field: value})


def test_widget_conversation_rejects_invalid_email():
    with pytest.raises(ValidationError):
        WidgetConversationCreate(
            full_name="John Smith",
            email="not-an-email",
            message="I need help",
        )


def test_widget_conversation_allows_missing_email():
    result = WidgetConversationCreate(
        full_name="John Smith",
        message="I need help",
    )
    assert result.email is None


def test_widget_message_rejects_whitespace():
    with pytest.raises(ValidationError):
        WidgetMessageCreate(message="   ")


def test_widget_message_trims_whitespace():
    result = WidgetMessageCreate(message="  Hello support  ")
    assert result.message == "Hello support"


from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
)
from app.schemas.knowledge_retrieval import KnowledgeSearchRequest
from app.schemas.organization_ai_settings import OrganizationAISettingsUpdate


def test_knowledge_base_create_trims_name():
    result = KnowledgeBaseCreate(name="  Customer Support  ")
    assert result.name == "Customer Support"


@pytest.mark.parametrize("name", ["", " ", "  "])
def test_knowledge_base_create_rejects_empty_name(name):
    with pytest.raises(ValidationError):
        KnowledgeBaseCreate(name=name)


def test_knowledge_base_update_trims_name():
    result = KnowledgeBaseUpdate(name="  Support Docs  ")
    assert result.name == "Support Docs"


def test_knowledge_base_update_rejects_null_name():
    with pytest.raises(ValidationError):
        KnowledgeBaseUpdate(name=None)


@pytest.mark.parametrize("name", ["", " ", "  ", "A"])
def test_knowledge_base_update_rejects_invalid_name(name):
    with pytest.raises(ValidationError):
        KnowledgeBaseUpdate(name=name)


def test_knowledge_base_update_allows_omitted_name():
    result = KnowledgeBaseUpdate(description="Updated description")
    assert "name" not in result.model_dump(exclude_unset=True)


def test_knowledge_search_trims_query():
    result = KnowledgeSearchRequest(query="  refund policy  ")
    assert result.query == "refund policy"


@pytest.mark.parametrize("query", ["", " ", "  ", "\t\n"])
def test_knowledge_search_rejects_empty_query(query):
    with pytest.raises(ValidationError):
        KnowledgeSearchRequest(query=query)


def test_knowledge_search_rejects_limit_above_maximum():
    with pytest.raises(ValidationError):
        KnowledgeSearchRequest(query="refund policy", limit=21)


def test_knowledge_search_rejects_zero_limit():
    with pytest.raises(ValidationError):
        KnowledgeSearchRequest(query="refund policy", limit=0)


def test_ai_settings_update_allows_partial_update():
    result = OrganizationAISettingsUpdate(ai_enabled=False)
    assert result.model_dump(exclude_unset=True) == {"ai_enabled": False}


def test_ai_settings_update_ignores_explicit_null_values():
    result = OrganizationAISettingsUpdate(confidence_threshold=None)
    assert result.confidence_threshold is None
