from app.models.conversation_ai_insight import ConversationAIInsight


def create_review_setup(client, db_session, email):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Review Tester",
            "email": email,
            "password": "TestPassword123!",
            "organization_name": f"Organization {email}",
        },
    )

    assert registration.status_code == 201

    registration_data = registration.json()

    auth = {
        "Authorization": f"Bearer {registration_data['access_token']}",
        "X-Organization-ID": registration_data["organizations"][0]["id"],
}

    

    customer_response = client.post(
        "/api/v1/customers",
        headers=auth,
        json={
        "full_name": "Review Customer",
        "email": f"customer-{email}",
        "phone": "03001234567",
        "company": "Test Company",
},
       
    )

    assert customer_response.status_code == 201, customer_response.json()

    conversation_response = client.post(
        "/api/v1/conversations",
        headers=auth,
        json={
            "customer_id": customer_response.json()["id"],
            "subject": "AI suggestion review test",
            "priority": "normal",
            "channel": "web_widget",
        },
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]
    organization_id = registration.json()["organizations"][0]["id"]
    user_id = registration.json()["user"]["id"]

    insight = ConversationAIInsight(
        organization_id=organization_id,
        conversation_id=conversation_id,
        intent="general_support",
        sentiment="neutral",
        priority="normal",
        confidence=0.95,
        requires_human=False,
        reasoning="Test reasoning",
        suggested_reply="Here is a test AI suggestion.",
        suggestion_status="pending",
    )

    db_session.add(insight)
    db_session.commit()

    return auth, conversation_id, user_id, insight


def test_approve_ai_suggestion(client, db_session):
    auth, conversation_id, user_id, insight = create_review_setup(
        client, db_session, "approve@example.com"
    )

    response = client.patch(
        f"/api/v1/conversations/{conversation_id}/ai/review",
        headers=auth,
        json={"decision": "approved"},
    )

    assert response.status_code == 200
    assert response.json()["suggestion_status"] == "approved"
    assert response.json()["reviewed_by_id"] == user_id
    assert response.json()["reviewed_at"] is not None

    db_session.refresh(insight)
    assert insight.suggestion_status == "approved"


def test_reject_ai_suggestion(client, db_session):
    auth, conversation_id, _, insight = create_review_setup(
        client, db_session, "reject@example.com"
    )

    response = client.patch(
        f"/api/v1/conversations/{conversation_id}/ai/review",
        headers=auth,
        json={"decision": "rejected"},
    )

    assert response.status_code == 200
    assert response.json()["suggestion_status"] == "rejected"

    db_session.refresh(insight)
    assert insight.suggestion_status == "rejected"


def test_prevent_second_ai_suggestion_review(client, db_session):
    auth, conversation_id, _, insight = create_review_setup(
        client, db_session, "duplicate-review@example.com"
    )

    first_response = client.patch(
        f"/api/v1/conversations/{conversation_id}/ai/review",
        headers=auth,
        json={"decision": "approved"},
    )

    assert first_response.status_code == 200

    second_response = client.patch(
        f"/api/v1/conversations/{conversation_id}/ai/review",
        headers=auth,
        json={"decision": "rejected"},
    )

    assert second_response.status_code == 409

    db_session.refresh(insight)
    assert insight.suggestion_status == "approved"


def test_prevent_cross_organization_ai_suggestion_review(
    client, db_session
):
    _, conversation_id, _, insight = create_review_setup(
        client, db_session, "first-org@example.com"
    )

    other_auth, _, _, _ = create_review_setup(
        client, db_session, "second-org@example.com"
    )

    response = client.patch(
        f"/api/v1/conversations/{conversation_id}/ai/review",
        headers=other_auth,
        json={"decision": "approved"},
    )

    assert response.status_code == 404

    db_session.refresh(insight)
    assert insight.suggestion_status == "pending"