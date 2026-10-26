"""Tests for the publish flow, run against the real WooCommerceConnector
code with its HTTP layer mocked via respx (no live WooCommerce store is
available in this sandbox). The connector logic under test — idempotent
create, SKU-based reconciliation after a timeout, retry/backoff, update vs
create branching — is exactly what would run against a real store; only
the transport is faked. This is explicitly NOT a claim that the connector
has been verified against a real WooCommerce installation."""

import httpx
import respx

from tests.helpers import auth_headers

WC_BASE = "https://woo-test.example.com/wp-json/wc/v3"


def _create_product(client, headers, sku="WC-SKU-1", **overrides):
    payload = {"sku": sku, "title": "WooCommerce测试商品", "price": "25.00", "category": "测试分类"}
    payload.update(overrides)
    resp = client.post("/api/v1/products", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_woocommerce_site(client, headers, base_url="https://woo-test.example.com"):
    resp = client.post(
        "/api/v1/sites",
        json={
            "name": "WooCommerce测试站",
            "platform": "woocommerce",
            "base_url": base_url,
            "credentials": {"key": "ck_test", "secret": "cs_test"},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bind(client, headers, product_id, site_id):
    resp = client.post(
        "/api/v1/site-products", json={"product_id": product_id, "site_id": site_id}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_first_publish_creates_remote_product(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)
    site = _create_woocommerce_site(client, headers)
    sp = _bind(client, headers, product["id"], site["id"])

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        mock.get("/products", params={"sku": "WC-SKU-1"}).respond(200, json=[])
        mock.post("/products").respond(
            201, json={"id": 4242, "sku": "WC-SKU-1", "name": "WooCommerce测试商品"}
        )

        resp = client.post(
            "/api/v1/publications",
            json={"site_id": site["id"], "site_product_ids": [sp["id"]]},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["success_items"] == 1
    assert body["items"][0]["external_id"] == "4242"

    detail = client.get(f"/api/v1/site-products/{sp['id']}", headers=headers).json()
    assert detail["status"] == "published"


def test_publish_finds_existing_remote_product_by_sku_instead_of_duplicating(client):
    """Idempotency: if a remote product with this SKU already exists (e.g.
    from an earlier partial run), publish must adopt it rather than POST a
    second one."""
    headers = auth_headers(client)
    product = _create_product(client, headers, sku="ALREADY-EXISTS")
    site = _create_woocommerce_site(client, headers)
    sp = _bind(client, headers, product["id"], site["id"])

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        find_route = mock.get("/products", params={"sku": "ALREADY-EXISTS"}).respond(
            200, json=[{"id": 999, "sku": "ALREADY-EXISTS"}]
        )
        create_route = mock.post("/products")  # must NOT be called

        resp = client.post(
            "/api/v1/publications",
            json={"site_id": site["id"], "site_product_ids": [sp["id"]]},
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["items"][0]["external_id"] == "999"
    assert find_route.called
    assert not create_route.called


def test_timeout_then_reconciliation_avoids_duplicate_creation(client):
    """The required behavior: if create times out, query remote state
    before retrying/creating again."""
    headers = auth_headers(client)
    product = _create_product(client, headers, sku="TIMEOUT-SKU")
    site = _create_woocommerce_site(client, headers)
    sp = _bind(client, headers, product["id"], site["id"])

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        # First SKU lookup (before creating): nothing yet.
        # Create: times out.
        # Reconciliation SKU lookup: now it exists (created server-side
        # despite the client-perceived timeout).
        mock.get("/products", params={"sku": "TIMEOUT-SKU"}).side_effect = [
            httpx.Response(200, json=[]),
            httpx.Response(200, json=[{"id": 777, "sku": "TIMEOUT-SKU"}]),
        ]
        mock.post("/products").side_effect = httpx.TimeoutException("simulated timeout")

        resp = client.post(
            "/api/v1/publications",
            json={"site_id": site["id"], "site_product_ids": [sp["id"]]},
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert body["items"][0]["external_id"] == "777"


def test_republish_is_update_not_create(client):
    headers = auth_headers(client)
    product = _create_product(client, headers, sku="UPDATE-SKU")
    site = _create_woocommerce_site(client, headers)
    sp = _bind(client, headers, product["id"], site["id"])

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        mock.get("/products", params={"sku": "UPDATE-SKU"}).respond(200, json=[])
        mock.post("/products").respond(201, json={"id": 123, "sku": "UPDATE-SKU"})
        client.post(
            "/api/v1/publications",
            json={"site_id": site["id"], "site_product_ids": [sp["id"]]},
            headers=headers,
        )

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        update_route = mock.put("/products/123").respond(200, json={"id": 123, "sku": "UPDATE-SKU"})
        find_route = mock.get("/products", params={"sku": "UPDATE-SKU"})  # must NOT be called

        resp = client.post(
            "/api/v1/publications",
            json={"site_id": site["id"], "site_product_ids": [sp["id"]]},
            headers=headers,
        )

    assert resp.status_code == 201
    assert resp.json()["items"][0]["external_id"] == "123"
    assert update_route.called
    assert not find_route.called


def test_one_item_failure_does_not_affect_other_items_in_same_job(client):
    headers = auth_headers(client)
    good_product = _create_product(client, headers, sku="GOOD-SKU")
    bad_product = _create_product(client, headers, sku="BAD-SKU")
    site = _create_woocommerce_site(client, headers)
    sp_good = _bind(client, headers, good_product["id"], site["id"])
    sp_bad = _bind(client, headers, bad_product["id"], site["id"])

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        mock.get("/products", params={"sku": "GOOD-SKU"}).respond(200, json=[])
        mock.post("/products", json__sku="GOOD-SKU").respond(201, json={"id": 1, "sku": "GOOD-SKU"})
        mock.get("/products", params={"sku": "BAD-SKU"}).respond(200, json=[])
        mock.post("/products", json__sku="BAD-SKU").respond(
            422, json={"message": "Invalid product data"}
        )

        resp = client.post(
            "/api/v1/publications",
            json={"site_id": site["id"], "site_product_ids": [sp_good["id"], sp_bad["id"]]},
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "partial"
    assert body["success_items"] == 1
    assert body["failed_items"] == 1

    good_detail = client.get(f"/api/v1/site-products/{sp_good['id']}", headers=headers).json()
    bad_detail = client.get(f"/api/v1/site-products/{sp_bad['id']}", headers=headers).json()
    assert good_detail["status"] == "published"
    assert bad_detail["status"] == "failed"


def test_retry_failed_only_touches_failed_items(client):
    headers = auth_headers(client)
    good_product = _create_product(client, headers, sku="RETRY-GOOD")
    bad_product = _create_product(client, headers, sku="RETRY-BAD")
    site = _create_woocommerce_site(client, headers)
    sp_good = _bind(client, headers, good_product["id"], site["id"])
    sp_bad = _bind(client, headers, bad_product["id"], site["id"])

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        mock.get("/products", params={"sku": "RETRY-GOOD"}).respond(200, json=[])
        mock.post("/products", json__sku="RETRY-GOOD").respond(201, json={"id": 1, "sku": "RETRY-GOOD"})
        mock.get("/products", params={"sku": "RETRY-BAD"}).respond(200, json=[])
        mock.post("/products", json__sku="RETRY-BAD").respond(500, json={"message": "server error"})

        created = client.post(
            "/api/v1/publications",
            json={"site_id": site["id"], "site_product_ids": [sp_good["id"], sp_bad["id"]]},
            headers=headers,
        ).json()

    assert created["status"] == "partial"

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        good_create_route = mock.post("/products", json__sku="RETRY-GOOD")  # must NOT be called again
        mock.get("/products", params={"sku": "RETRY-BAD"}).respond(200, json=[])
        mock.post("/products", json__sku="RETRY-BAD").respond(201, json={"id": 99, "sku": "RETRY-BAD"})

        retried = client.post(f"/api/v1/publications/{created['id']}/retry-failed", headers=headers)

    assert retried.status_code == 200
    body = retried.json()
    assert body["status"] == "completed"
    assert body["success_items"] == 2
    assert body["failed_items"] == 0
    assert not good_create_route.called

    bad_detail = client.get(f"/api/v1/site-products/{sp_bad['id']}", headers=headers).json()
    assert bad_detail["status"] == "published"


def test_publish_requires_existing_site(client):
    headers = auth_headers(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(
        "/api/v1/publications", json={"site_id": fake_id, "site_product_ids": [fake_id]}, headers=headers
    )
    assert resp.status_code == 404


def test_publish_rejects_bindings_not_belonging_to_site(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)
    site_a = _create_woocommerce_site(client, headers, base_url="https://a.example.com")
    site_b = _create_woocommerce_site(client, headers, base_url="https://b.example.com")
    sp_on_a = _bind(client, headers, product["id"], site_a["id"])

    resp = client.post(
        "/api/v1/publications",
        json={"site_id": site_b["id"], "site_product_ids": [sp_on_a["id"]]},
        headers=headers,
    )
    assert resp.status_code == 400


def test_get_publication_job_not_found(client):
    headers = auth_headers(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/publications/{fake_id}", headers=headers)
    assert resp.status_code == 404


def test_retry_failed_with_no_failures_is_a_noop(client):
    headers = auth_headers(client)
    product = _create_product(client, headers, sku="NOOP-SKU")
    site = _create_woocommerce_site(client, headers)
    sp = _bind(client, headers, product["id"], site["id"])

    with respx.mock(base_url=WC_BASE, assert_all_called=False) as mock:
        mock.get("/products", params={"sku": "NOOP-SKU"}).respond(200, json=[])
        mock.post("/products").respond(201, json={"id": 1, "sku": "NOOP-SKU"})
        created = client.post(
            "/api/v1/publications",
            json={"site_id": site["id"], "site_product_ids": [sp["id"]]},
            headers=headers,
        ).json()

    assert created["status"] == "completed"

    retried = client.post(f"/api/v1/publications/{created['id']}/retry-failed", headers=headers)
    assert retried.status_code == 200
    assert retried.json()["status"] == "completed"
    assert retried.json()["success_items"] == 1


def test_publish_to_shopify_site_fails_loudly_not_silently(client):
    """No Shopify connector exists yet (Phase 6) — publishing to one must
    fail with a clear per-item error, never silently report success."""
    headers = auth_headers(client)
    product = _create_product(client, headers, sku="SHOPIFY-SKU")
    site = client.post(
        "/api/v1/sites",
        json={"name": "未实现的Shopify站", "platform": "shopify", "base_url": "https://shop.example.com"},
        headers=headers,
    ).json()
    sp = _bind(client, headers, product["id"], site["id"])

    resp = client.post(
        "/api/v1/publications", json={"site_id": site["id"], "site_product_ids": [sp["id"]]}, headers=headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed"
    assert "暂无可用连接器" in body["items"][0]["error_message"]


def test_publish_without_site_credentials_fails_clearly(client):
    headers = auth_headers(client)
    product = _create_product(client, headers, sku="NO-CREDS-SKU")
    site = client.post(
        "/api/v1/sites",
        json={"name": "无凭据站", "platform": "woocommerce", "base_url": "https://nocreds.example.com"},
        headers=headers,
    ).json()
    sp = _bind(client, headers, product["id"], site["id"])

    resp = client.post(
        "/api/v1/publications", json={"site_id": site["id"], "site_product_ids": [sp["id"]]}, headers=headers
    )
    body = resp.json()
    assert body["status"] == "failed"
    assert "未配置访问凭据" in body["items"][0]["error_message"]


def test_publish_with_incomplete_credentials_fails_clearly(client):
    headers = auth_headers(client)
    product = _create_product(client, headers, sku="BAD-CREDS-SKU")
    site = client.post(
        "/api/v1/sites",
        json={
            "name": "凭据不全的站", "platform": "woocommerce", "base_url": "https://partial.example.com",
            "credentials": {"key": "only_a_key_no_secret"},
        },
        headers=headers,
    ).json()
    sp = _bind(client, headers, product["id"], site["id"])

    resp = client.post(
        "/api/v1/publications", json={"site_id": site["id"], "site_product_ids": [sp["id"]]}, headers=headers
    )
    body = resp.json()
    assert body["status"] == "failed"
    assert "缺少 consumer key/secret" in body["items"][0]["error_message"]


def test_only_admin_or_operator_can_publish(client):
    admin_headers = auth_headers(client)
    client.post(
        "/api/v1/auth/users",
        json={"email": "reviewer@example.com", "password": "ReviewerPass1", "role": "reviewer"},
        headers=admin_headers,
    )
    from tests.helpers import login

    reviewer_tokens = login(client, "reviewer@example.com", "ReviewerPass1")
    reviewer_headers = {"Authorization": f"Bearer {reviewer_tokens['access_token']}"}

    product = _create_product(client, admin_headers)
    site = _create_woocommerce_site(client, admin_headers)
    sp = _bind(client, admin_headers, product["id"], site["id"])

    resp = client.post(
        "/api/v1/publications",
        json={"site_id": site["id"], "site_product_ids": [sp["id"]]},
        headers=reviewer_headers,
    )
    assert resp.status_code == 403

    # But a reviewer CAN view job history.
    listed = client.get("/api/v1/publications", headers=reviewer_headers)
    assert listed.status_code == 200
