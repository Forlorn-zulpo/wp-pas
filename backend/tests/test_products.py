from tests.helpers import auth_headers, bootstrap_admin, login


def _create_product(client, headers, **overrides):
    payload = {
        "sku": "SKU-0001",
        "title": "测试商品",
        "price": "19.99",
        "category": "电子",
    }
    payload.update(overrides)
    resp = client.post("/api/v1/products", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_product_and_duplicate_sku_rejected(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)
    assert product["sku"] == "SKU-0001"
    assert product["status"] == "draft"
    assert product["version"] == 1

    dup = client.post(
        "/api/v1/products",
        json={"sku": "SKU-0001", "title": "重复商品", "price": "5"},
        headers=headers,
    )
    assert dup.status_code == 409


def test_readonly_cannot_create_product(client):
    admin_headers = auth_headers(client)
    client.post(
        "/api/v1/auth/users",
        json={"email": "ro@example.com", "password": "ReadonlyPass1", "role": "readonly"},
        headers=admin_headers,
    )
    ro_tokens = login(client, "ro@example.com", "ReadonlyPass1")
    ro_headers = {"Authorization": f"Bearer {ro_tokens['access_token']}"}

    resp = client.post(
        "/api/v1/products", json={"sku": "X-1", "title": "x", "price": "1"}, headers=ro_headers
    )
    assert resp.status_code == 403

    # But readonly CAN list/read.
    listed = client.get("/api/v1/products", headers=ro_headers)
    assert listed.status_code == 200


def test_list_products_pagination_filter_search_sort(client):
    headers = auth_headers(client)
    for i in range(5):
        _create_product(
            client, headers, sku=f"SKU-{i:04d}", title=f"商品{i}",
            price=str(10 + i), category="鞋类" if i % 2 == 0 else "服装",
        )

    page1 = client.get("/api/v1/products?page=1&page_size=2", headers=headers).json()
    assert page1["total"] == 5
    assert len(page1["items"]) == 2

    page2 = client.get("/api/v1/products?page=2&page_size=2", headers=headers).json()
    assert len(page2["items"]) == 2
    assert {p["id"] for p in page1["items"]}.isdisjoint({p["id"] for p in page2["items"]})

    shoes = client.get("/api/v1/products?category=鞋类", headers=headers).json()
    assert shoes["total"] == 3
    assert all(p["category"] == "鞋类" for p in shoes["items"])

    search = client.get("/api/v1/products?search=商品2", headers=headers).json()
    assert search["total"] == 1

    sorted_asc = client.get(
        "/api/v1/products?sort_by=price&sort_dir=asc&page_size=50", headers=headers
    ).json()
    prices = [float(p["price"]) for p in sorted_asc["items"]]
    assert prices == sorted(prices)

    bad_sort = client.get("/api/v1/products?sort_by=not_a_field", headers=headers)
    assert bad_sort.status_code == 400


def test_get_product_detail_includes_variants_and_assets(client):
    headers = auth_headers(client)
    product = _create_product(
        client, headers,
        variants=[{"sku": "VAR-1", "options": {"color": "红"}, "stock_quantity": 10}],
    )
    detail = client.get(f"/api/v1/products/{product['id']}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["variants"]) == 1
    assert body["variants"][0]["sku"] == "VAR-1"
    assert body["assets"] == []

    missing = client.get(
        "/api/v1/products/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert missing.status_code == 404


def test_update_product_optimistic_locking(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)

    ok = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"version": 1, "title": "新标题"},
        headers=headers,
    )
    assert ok.status_code == 200
    assert ok.json()["title"] == "新标题"
    assert ok.json()["version"] == 2

    # Stale version (still 1) must now be rejected with 409.
    stale = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"version": 1, "title": "另一个标题"},
        headers=headers,
    )
    assert stale.status_code == 409


def test_archive_product_is_soft_delete(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)

    resp = client.delete(f"/api/v1/products/{product['id']}", headers=headers)
    assert resp.status_code == 204

    detail = client.get(f"/api/v1/products/{product['id']}", headers=headers).json()
    assert detail["status"] == "archived"  # row still exists — not hard-deleted


def test_bulk_update_products(client):
    headers = auth_headers(client)
    ids = [_create_product(client, headers, sku=f"BULK-{i}")["id"] for i in range(3)]
    fake_id = "00000000-0000-0000-0000-000000000000"

    resp = client.post(
        "/api/v1/products/bulk-update",
        json={"ids": ids + [fake_id], "status": "active", "brand": "共享品牌"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["updated_count"] == 3
    assert body["not_found_ids"] == [fake_id]

    for pid in ids:
        detail = client.get(f"/api/v1/products/{pid}", headers=headers).json()
        assert detail["status"] == "active"
        assert detail["brand"] == "共享品牌"


def test_variant_crud(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)

    added = client.post(
        f"/api/v1/products/{product['id']}/variants",
        json={"sku": "VAR-ADD-1", "options": {"size": "L"}, "stock_quantity": 5},
        headers=headers,
    )
    assert added.status_code == 201
    variant_id = added.json()["id"]

    dup = client.post(
        f"/api/v1/products/{product['id']}/variants",
        json={"sku": "VAR-ADD-1", "options": {}},
        headers=headers,
    )
    assert dup.status_code == 409

    updated = client.patch(
        f"/api/v1/products/{product['id']}/variants/{variant_id}",
        json={"stock_quantity": 99},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["stock_quantity"] == 99

    deleted = client.delete(
        f"/api/v1/products/{product['id']}/variants/{variant_id}", headers=headers
    )
    assert deleted.status_code == 204

    detail = client.get(f"/api/v1/products/{product['id']}", headers=headers).json()
    assert detail["variants"] == []
