from tests.helpers import auth_headers


def _create_site(client, headers, **overrides):
    payload = {
        "name": "测试站点",
        "platform": "woocommerce",
        "base_url": "https://example.com",
        "credentials": {"consumer_key": "ck_test", "consumer_secret": "cs_test"},
    }
    payload.update(overrides)
    resp = client.post("/api/v1/sites", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_site_never_returns_raw_credentials(client):
    headers = auth_headers(client)
    site = _create_site(client, headers)
    assert site["has_credentials"] is True
    assert "credentials" not in site
    assert "encrypted_credentials" not in site
    assert site["platform"] == "woocommerce"


def test_credentials_are_actually_encrypted_in_the_database(client):
    headers = auth_headers(client)
    _create_site(client, headers)

    # Plain psycopg2 (sync driver, its own throwaway connection) — avoids
    # touching the app's asyncpg engine from outside its own event loop,
    # which previously crashed the whole test process.
    import psycopg2

    conn = psycopg2.connect(
        host="localhost", port=5432, dbname="app_test_db", user="postgres", password="postgres"
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT encrypted_credentials FROM sites LIMIT 1")
            raw = cur.fetchone()[0]
    finally:
        conn.close()

    assert raw is not None
    assert "ck_test" not in raw  # plaintext key must not appear anywhere in the stored blob


def test_only_admin_can_create_site(client):
    admin_headers = auth_headers(client)
    client.post(
        "/api/v1/auth/users",
        json={"email": "op@example.com", "password": "OperatorPass1", "role": "operator"},
        headers=admin_headers,
    )
    from tests.helpers import login

    op_tokens = login(client, "op@example.com", "OperatorPass1")
    op_headers = {"Authorization": f"Bearer {op_tokens['access_token']}"}

    resp = client.post(
        "/api/v1/sites",
        json={"name": "x", "platform": "shopify", "base_url": "https://x.com"},
        headers=op_headers,
    )
    assert resp.status_code == 403


def test_update_site_optimistic_lock_and_credential_rotation(client):
    headers = auth_headers(client)
    site = _create_site(client, headers)

    updated = client.patch(
        f"/api/v1/sites/{site['id']}",
        json={"version": 1, "name": "改名后的站点"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "改名后的站点"
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/sites/{site['id']}", json={"version": 1, "name": "x"}, headers=headers
    )
    assert stale.status_code == 409

    rotated = client.patch(
        f"/api/v1/sites/{site['id']}",
        json={"version": 2, "credentials": {"consumer_key": "new_key", "consumer_secret": "new_secret"}},
        headers=headers,
    )
    assert rotated.status_code == 200
    assert rotated.json()["has_credentials"] is True
    assert rotated.json()["last_connection_test_ok"] is None  # invalidated by rotation


def test_connection_test_against_reachable_host_reports_success(client):
    # pypi.org is on this sandbox's network allow-list, so this is a real
    # HTTP round trip, not a mock — the same code path a real site would hit.
    headers = auth_headers(client)
    site = _create_site(client, headers, base_url="https://pypi.org", name="可达站点")

    resp = client.post(f"/api/v1/sites/{site['id']}/test-connection", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "200" in body["message"] or "30" in body["message"]


def test_connection_test_against_unreachable_host_reports_failure(client):
    headers = auth_headers(client)
    site = _create_site(
        client, headers, base_url="http://this-host-does-not-exist.invalid.test"
    )

    resp = client.post(f"/api/v1/sites/{site['id']}/test-connection", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["message"]

    detail = client.get(f"/api/v1/sites/{site['id']}", headers=headers).json()
    assert detail["last_connection_test_ok"] is False
    assert detail["last_connection_test_at"] is not None
