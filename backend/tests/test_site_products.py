from tests.helpers import auth_headers


def _create_product(client, headers, **overrides):
    payload = {"sku": "SP-SKU-1", "title": "内部商品标题", "price": "20.00", "category": "原始分类"}
    payload.update(overrides)
    resp = client.post("/api/v1/products", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_site(client, headers, **overrides):
    payload = {"name": "站点A", "platform": "shopify", "base_url": "https://a.example.com"}
    payload.update(overrides)
    resp = client.post("/api/v1/sites", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_bind_product_to_site_and_duplicate_rejected(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)
    site = _create_site(client, headers)

    resp = client.post(
        "/api/v1/site-products",
        json={"product_id": product["id"], "site_id": site["id"]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "bound"
    assert body["override"]["title"] is None

    dup = client.post(
        "/api/v1/site-products",
        json={"product_id": product["id"], "site_id": site["id"]},
        headers=headers,
    )
    assert dup.status_code == 409


def test_bind_requires_existing_product_and_site(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)
    site = _create_site(client, headers)
    fake_id = "00000000-0000-0000-0000-000000000000"

    missing_product = client.post(
        "/api/v1/site-products", json={"product_id": fake_id, "site_id": site["id"]}, headers=headers
    )
    assert missing_product.status_code == 404

    missing_site = client.post(
        "/api/v1/site-products", json={"product_id": product["id"], "site_id": fake_id}, headers=headers
    )
    assert missing_site.status_code == 404


def test_get_site_product_not_found(client):
    headers = auth_headers(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/site-products/{fake_id}", headers=headers)
    assert resp.status_code == 404


def test_override_does_not_mutate_internal_product_or_other_site(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)
    site_a = _create_site(client, headers, name="站点A", base_url="https://a.example.com")
    site_b = _create_site(client, headers, name="站点B", base_url="https://b.example.com")

    sp_a = client.post(
        "/api/v1/site-products",
        json={"product_id": product["id"], "site_id": site_a["id"]},
        headers=headers,
    ).json()
    sp_b = client.post(
        "/api/v1/site-products",
        json={"product_id": product["id"], "site_id": site_b["id"]},
        headers=headers,
    ).json()

    updated = client.patch(
        f"/api/v1/site-products/{sp_a['id']}/override",
        json={"title": "站点A专属标题", "price": "99.99"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["override"]["title"] == "站点A专属标题"

    # Internal product must be untouched.
    product_after = client.get(f"/api/v1/products/{product['id']}", headers=headers).json()
    assert product_after["title"] == "内部商品标题"
    assert product_after["price"] == "20.00"

    # Site B's binding must be untouched.
    sp_b_after = client.get(f"/api/v1/site-products/{sp_b['id']}", headers=headers).json()
    assert sp_b_after["override"]["title"] is None


def test_publication_preview_merges_overrides_with_internal_product(client):
    headers = auth_headers(client)
    product = _create_product(client, headers, category="原始分类")
    site = _create_site(client, headers)
    sp = client.post(
        "/api/v1/site-products",
        json={"product_id": product["id"], "site_id": site["id"]},
        headers=headers,
    ).json()

    # No overrides yet: preview should equal the internal product verbatim.
    preview_before = client.get(f"/api/v1/publication-previews/{sp['id']}", headers=headers).json()
    assert preview_before["title"] == "内部商品标题"
    assert preview_before["category"] == "原始分类"
    assert preview_before["overridden_fields"] == []

    client.patch(
        f"/api/v1/site-products/{sp['id']}/override",
        json={"title": "站点专属标题"},
        headers=headers,
    )

    preview_after = client.get(f"/api/v1/publication-previews/{sp['id']}", headers=headers).json()
    assert preview_after["title"] == "站点专属标题"
    assert preview_after["category"] == "原始分类"  # not overridden, still inherited
    assert preview_after["overridden_fields"] == ["title"]


def test_unbind_requires_not_published_and_removes_binding(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)
    site = _create_site(client, headers)
    sp = client.post(
        "/api/v1/site-products",
        json={"product_id": product["id"], "site_id": site["id"]},
        headers=headers,
    ).json()

    deleted = client.delete(f"/api/v1/site-products/{sp['id']}", headers=headers)
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/site-products/{sp['id']}", headers=headers)
    assert missing.status_code == 404


def test_list_site_products_filters_by_product_and_site(client):
    headers = auth_headers(client)
    product1 = _create_product(client, headers, sku="FILT-1")
    product2 = _create_product(client, headers, sku="FILT-2")
    site = _create_site(client, headers)

    client.post(
        "/api/v1/site-products",
        json={"product_id": product1["id"], "site_id": site["id"]},
        headers=headers,
    )
    client.post(
        "/api/v1/site-products",
        json={"product_id": product2["id"], "site_id": site["id"]},
        headers=headers,
    )

    by_product = client.get(
        f"/api/v1/site-products?product_id={product1['id']}", headers=headers
    ).json()
    assert len(by_product) == 1
    assert by_product[0]["product_id"] == product1["id"]

    by_site = client.get(f"/api/v1/site-products?site_id={site['id']}", headers=headers).json()
    assert len(by_site) == 2
