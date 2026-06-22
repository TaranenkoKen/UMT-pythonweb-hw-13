"""Integration tests for all API routes."""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import date


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_signup(client):
    with patch("main.send_verification_email", new_callable=AsyncMock):
        resp = client.post("/auth/signup", json={"email": "new@example.com", "password": "pass123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert not data["is_verified"]


def test_signup_duplicate(client):
    with patch("main.send_verification_email", new_callable=AsyncMock):
        client.post("/auth/signup", json={"email": "dup@example.com", "password": "pass123"})
        resp = client.post("/auth/signup", json={"email": "dup@example.com", "password": "pass123"})
    assert resp.status_code == 409


def test_login_success(client, test_user):
    resp = client.post("/auth/login", data={"username": test_user.email, "password": "password123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client, test_user):
    resp = client.post("/auth/login", data={"username": test_user.email, "password": "wrongpass"})
    assert resp.status_code == 401


def test_verify_email_invalid_token(client):
    resp = client.get("/auth/verify/badtoken")
    assert resp.status_code == 400


def test_verify_email_valid(client):
    import auth
    token = auth.create_email_token("new@example.com")
    resp = client.get(f"/auth/verify/{token}")
    # user may or may not exist in this db state — just check not 400 token error
    assert resp.status_code in (200, 404)


def test_refresh_tokens_invalid(client):
    resp = client.post("/auth/refresh", params={"refresh_token": "bad.token"})
    assert resp.status_code == 401


def test_refresh_tokens_valid(client, test_user):
    import auth
    refresh = auth.create_refresh_token({"sub": test_user.email})
    resp = client.post("/auth/refresh", params={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def test_request_password_reset_unknown_email(client):
    with patch("main.send_password_reset_email", new_callable=AsyncMock):
        resp = client.post("/auth/request-password-reset", json={"email": "nobody@example.com"})
    assert resp.status_code == 200  # always 200 to avoid enumeration


def test_request_password_reset_known_email(client, test_user):
    with patch("main.send_password_reset_email", new_callable=AsyncMock):
        resp = client.post("/auth/request-password-reset", json={"email": test_user.email})
    assert resp.status_code == 200


def test_reset_password_invalid_token(client):
    resp = client.post("/auth/reset-password", json={"token": "bad", "new_password": "newpass123"})
    assert resp.status_code == 400


def test_reset_password_valid(client, test_user):
    import auth
    token = auth.create_password_reset_token(test_user.email)
    resp = client.post("/auth/reset-password", json={"token": token, "new_password": "newpass123"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def test_get_me_unauthorized(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_get_me_authorized(client, user_token):
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200


def test_update_avatar_forbidden_for_regular_user(client, user_token):
    resp = client.patch(
        "/users/avatar",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("avatar.png", b"fake-image-data", "image/png")},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

CONTACT_PAYLOAD = {
    "first_name": "Test",
    "last_name": "Contact",
    "email": "contact@example.com",
    "phone": "0991234567",
    "birthday": "1990-01-15",
}


def test_create_contact(client, user_token):
    resp = client.post("/contacts/", json=CONTACT_PAYLOAD, headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 201
    assert resp.json()["first_name"] == "Test"


def test_get_contacts(client, user_token):
    resp = client.get("/contacts/", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_contact_not_found(client, user_token):
    resp = client.get("/contacts/99999", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 404


def test_update_contact(client, user_token):
    create_resp = client.post("/contacts/", json=CONTACT_PAYLOAD, headers={"Authorization": f"Bearer {user_token}"})
    contact_id = create_resp.json()["id"]

    updated = {**CONTACT_PAYLOAD, "first_name": "Updated"}
    resp = client.put(f"/contacts/{contact_id}", json=updated, headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"


def test_delete_contact(client, user_token):
    create_resp = client.post("/contacts/", json=CONTACT_PAYLOAD, headers={"Authorization": f"Bearer {user_token}"})
    contact_id = create_resp.json()["id"]

    resp = client.delete(f"/contacts/{contact_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 204


def test_delete_contact_not_found(client, user_token):
    resp = client.delete("/contacts/99999", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 404


def test_birthdays_endpoint(client, user_token):
    resp = client.get("/contacts/birthdays", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
