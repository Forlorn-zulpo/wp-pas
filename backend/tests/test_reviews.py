from tests.helpers import auth_headers, login


def _setup_binding(client, headers):
    product = client.post(
        "/api/v1/products", json={"sku": "REV-SKU-1", "title": "待审核商品", "price": "15"},
        headers=headers,
    ).json()
    site = client.post(
        "/api/v1/sites",
        json={"name": "审核测试站", "platform": "woocommerce", "base_url": "https://review-test.example.com"},
        headers=headers,
    ).json()
    sp = client.post(
        "/api/v1/site-products", json={"product_id": product["id"], "site_id": site["id"]}, headers=headers
    ).json()
    return product, site, sp


def test_request_review_blocks_duplicate_pending(client):
    headers = auth_headers(client)
    _, _, sp = _setup_binding(client, headers)

    first = client.post("/api/v1/reviews", json={"site_product_id": sp["id"]}, headers=headers)
    assert first.status_code == 201
    assert first.json()["status"] == "pending"

    dup = client.post("/api/v1/reviews", json={"site_product_id": sp["id"]}, headers=headers)
    assert dup.status_code == 409

    sp_after = client.get(f"/api/v1/site-products/{sp['id']}", headers=headers).json()
    assert sp_after["status"] == "pending_review"


def test_reviewer_can_approve_but_operator_cannot(client):
    admin_headers = auth_headers(client)
    _, _, sp = _setup_binding(client, admin_headers)
    review = client.post("/api/v1/reviews", json={"site_product_id": sp["id"]}, headers=admin_headers).json()

    client.post(
        "/api/v1/auth/users",
        json={"email": "op@example.com", "password": "OperatorPass1", "role": "operator"},
        headers=admin_headers,
    )
    op_tokens = login(client, "op@example.com", "OperatorPass1")
    op_headers = {"Authorization": f"Bearer {op_tokens['access_token']}"}

    forbidden = client.post(f"/api/v1/reviews/{review['id']}/approve", json={}, headers=op_headers)
    assert forbidden.status_code == 403

    approved = client.post(f"/api/v1/reviews/{review['id']}/approve", json={"notes": "看起来不错"}, headers=admin_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    sp_after = client.get(f"/api/v1/site-products/{sp['id']}", headers=admin_headers).json()
    assert sp_after["status"] == "approved"


def test_reject_sends_binding_back_to_bound(client):
    headers = auth_headers(client)
    _, _, sp = _setup_binding(client, headers)
    review = client.post("/api/v1/reviews", json={"site_product_id": sp["id"]}, headers=headers).json()

    rejected = client.post(f"/api/v1/reviews/{review['id']}/reject", json={"notes": "标题不合适"}, headers=headers)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    sp_after = client.get(f"/api/v1/site-products/{sp['id']}", headers=headers).json()
    assert sp_after["status"] == "bound"


def test_cannot_decide_already_decided_review(client):
    headers = auth_headers(client)
    _, _, sp = _setup_binding(client, headers)
    review = client.post("/api/v1/reviews", json={"site_product_id": sp["id"]}, headers=headers).json()
    client.post(f"/api/v1/reviews/{review['id']}/approve", json={}, headers=headers)

    again = client.post(f"/api/v1/reviews/{review['id']}/approve", json={}, headers=headers)
    assert again.status_code == 409


def test_publish_blocked_while_pending_review(client):
    """The actual gate enforced in app/api/v1/publications.py: a
    PENDING_REVIEW SiteProduct must fail immediately, never reach the
    connector."""
    headers = auth_headers(client)
    product, site, sp = _setup_binding(client, headers)
    client.post("/api/v1/reviews", json={"site_product_id": sp["id"]}, headers=headers)

    resp = client.post(
        "/api/v1/publications",
        json={"site_id": site["id"], "site_product_ids": [sp["id"]]},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed"
    assert "待审核" in body["items"][0]["error_message"]
