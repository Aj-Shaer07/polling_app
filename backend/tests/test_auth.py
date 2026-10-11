from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    pw = "supersecretpassword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_token_roundtrip():
    data = {"sub": "user-123", "role": "PROFESSOR"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-123"
    assert decoded["role"] == "PROFESSOR"


def test_login_flow(client, seeded_db):
    # Valid professor login
    resp = client.post("/api/auth/login", json={"username": "prof_turing", "password": "profpassword123"})
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    assert token_data["role"] == "PROFESSOR"

    # Invalid password login
    bad_resp = client.post("/api/auth/login", json={"username": "prof_turing", "password": "wrongpassword"})
    assert bad_resp.status_code == 401


def test_role_based_access_control(client, seeded_db):
    # Log in as professor
    prof_login = client.post("/api/auth/login", json={"username": "prof_turing", "password": "profpassword123"})
    prof_token = prof_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {prof_token}"}

    # Professor trying to access admin endpoint -> 403 Forbidden
    admin_resp = client.get("/api/admin/roster", headers=headers)
    assert admin_resp.status_code == 403

    # Clear cookies to test truly unauthenticated access
    client.cookies.clear()
    unauth_resp = client.get("/api/admin/roster")
    assert unauth_resp.status_code == 401

    # Log in as admin
    admin_login = client.post("/api/auth/login", json={"username": "admin_test", "password": "adminpassword123"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin accessing admin endpoint -> 200 OK
    admin_roster_resp = client.get("/api/admin/roster", headers=admin_headers)
    assert admin_roster_resp.status_code == 200
