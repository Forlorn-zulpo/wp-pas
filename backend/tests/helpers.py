def bootstrap_admin(client, email="admin@example.com", password="StrongPass123"):
    resp = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"email": email, "password": password, "full_name": "Admin"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def login(client, email, password):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_headers(client, email="admin@example.com", password="StrongPass123"):
    bootstrap_admin(client, email, password)
    tokens = login(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}
