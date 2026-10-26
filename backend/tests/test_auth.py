def _bootstrap_admin(client, email="admin@example.com", password="StrongPass123"):
    resp = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"email": email, "password": password, "full_name": "Admin"},
    )
    assert resp.status_code == 201
    return resp.json()


def _login(client, email, password):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()


def test_bootstrap_admin_only_works_once(client):
    _bootstrap_admin(client)
    resp = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"email": "second@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 403


def test_login_success_and_wrong_password(client):
    _bootstrap_admin(client)
    ok = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "StrongPass123"}
    )
    assert ok.status_code == 200
    assert "access_token" in ok.json()
    assert "refresh_token" in ok.json()

    bad = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong"}
    )
    assert bad.status_code == 401


def test_me_requires_valid_token(client):
    _bootstrap_admin(client)
    no_token = client.get("/api/v1/auth/me")
    assert no_token.status_code == 401

    tokens = _login(client, "admin@example.com", "StrongPass123")
    ok = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert ok.status_code == 200
    assert ok.json()["email"] == "admin@example.com"
    assert ok.json()["role"] == "admin"

    bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


def test_only_admin_can_create_users(client):
    _bootstrap_admin(client)
    admin_tokens = _login(client, "admin@example.com", "StrongPass123")
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}

    created = client.post(
        "/api/v1/auth/users",
        json={"email": "op@example.com", "password": "OperatorPass1", "role": "operator"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert created.json()["role"] == "operator"

    op_tokens = _login(client, "op@example.com", "OperatorPass1")
    op_headers = {"Authorization": f"Bearer {op_tokens['access_token']}"}

    forbidden = client.post(
        "/api/v1/auth/users",
        json={"email": "y@example.com", "password": "Pass12345"},
        headers=op_headers,
    )
    assert forbidden.status_code == 403


def test_cannot_register_duplicate_email(client):
    _bootstrap_admin(client)
    tokens = _login(client, "admin@example.com", "StrongPass123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    client.post(
        "/api/v1/auth/users",
        json={"email": "dup@example.com", "password": "Pass12345"},
        headers=headers,
    )
    dup = client.post(
        "/api/v1/auth/users",
        json={"email": "dup@example.com", "password": "Pass12345"},
        headers=headers,
    )
    assert dup.status_code == 409


def test_refresh_token_issues_new_access_token(client):
    _bootstrap_admin(client)
    tokens = _login(client, "admin@example.com", "StrongPass123")

    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.json()

    # An access token must not work as a refresh token.
    wrong_type = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert wrong_type.status_code == 401


def test_health_endpoint(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] is True
    # Redis is pinged for real here, not stubbed — this sandbox runs a real
    # redis-server alongside Postgres for the test suite.
    assert body["redis"] is True
    assert body["status"] == "ok"
