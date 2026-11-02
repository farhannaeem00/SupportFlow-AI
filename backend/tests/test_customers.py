
def register_owner(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Organization Owner",
            "email": email,
            "password": "OwnerPassword123!",
            "organization_name": "Test Organization",
        },
    )

    assert response.status_code == 201

    data = response.json()

    return {
        "token": data["access_token"],
        "organization_id": data["organization"]["id"],
    }


def auth_headers(account):
    return {
        "Authorization": f"Bearer {account['token']}",
        "X-Organization-ID": account["organization_id"],
    }



def create_test_customer(
    client,
    owner,
    email="customer@example.com",
    full_name="Ali Khan",
):
    return client.post(
        "/api/v1/customers",
        headers=auth_headers(owner),
        json={
            "full_name": full_name,
            "email": email,
            "phone": "03001234567",
            "company": "ABC Technologies",
        },
    )



def test_create_customer_success(client):
    owner = register_owner(client, "owner1@example.com")

    response = create_test_customer(client, owner)

    assert response.status_code == 201

    data = response.json()

    assert data["full_name"] == "Ali Khan"
    assert data["email"] == "customer@example.com"
    assert data["company"] == "ABC Technologies"
    assert data["is_active"] is True
    assert data["organization_id"] == owner["organization_id"]


def test_list_customers(client):
    owner = register_owner(client, "owner2@example.com")

    create_test_customer(client, owner, "customer1@example.com")
    create_test_customer(client, owner, "customer2@example.com")

    response = client.get(
        "/api/v1/customers",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_customer_by_id(client):
    owner = register_owner(client, "owner3@example.com")

    create_response = create_test_customer(client, owner)
    customer_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["id"] == customer_id



def test_search_customers(client):
    owner = register_owner(client, "owner4@example.com")

    create_test_customer(
        client,
        owner,
        "ali@example.com",
        "Ali Khan",
    )

    create_test_customer(
        client,
        owner,
        "sara@example.com",
        "Sara Ahmed",
    )

    response = client.get(
        "/api/v1/customers?search=Ali",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["full_name"] == "Ali Khan"



def test_customer_pagination(client):
    owner = register_owner(client, "owner5@example.com")

    create_test_customer(client, owner, "customer1@example.com")
    create_test_customer(client, owner, "customer2@example.com")
    create_test_customer(client, owner, "customer3@example.com")

    response = client.get(
        "/api/v1/customers?skip=0&limit=2",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_customer(client):
    owner = register_owner(client, "owner6@example.com")

    create_response = create_test_customer(client, owner)
    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers(owner),
        json={
            "full_name": "Ali Ahmed",
            "company": "New Technologies",
        },
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Ali Ahmed"
    assert response.json()["company"] == "New Technologies"


def test_duplicate_customer_email_rejected(client):
    owner = register_owner(client, "owner7@example.com")

    first = create_test_customer(client, owner, "duplicate@example.com")
    assert first.status_code == 201

    second = create_test_customer(client, owner, "duplicate@example.com")

    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_customer_soft_delete(client):
    owner = register_owner(client, "owner8@example.com")

    create_response = create_test_customer(client, owner)
    customer_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers(owner),
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == (
        "Customer deactivated successfully"
    )

    get_response = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers(owner),
    )

    assert get_response.status_code == 404


def test_user_cannot_access_another_organizations_customer(client):
    owner_one = register_owner(client, "owner9@example.com")
    owner_two = register_owner(client, "owner10@example.com")

    create_response = create_test_customer(client, owner_two)
    customer_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 404


def test_invalid_customer_email_rejected(client):
    owner = register_owner(client, "owner11@example.com")

    response = client.post(
        "/api/v1/customers",
        headers=auth_headers(owner),
        json={
            "full_name": "Test Customer",
            "email": "not-a-valid-email",
        },
    )

    assert response.status_code == 422
