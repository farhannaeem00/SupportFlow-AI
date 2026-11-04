
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
