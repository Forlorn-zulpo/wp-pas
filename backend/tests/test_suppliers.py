from tests.helpers import auth_headers


def test_create_and_update_supplier_with_optimistic_lock(client):
    headers = auth_headers(client)
    created = client.post(
        "/api/v1/suppliers",
        json={
            "name": "测试供应商",
            "website": "https://supplier.example.com",
            "collection_method": "manual",
            "credentials": {"api_key": "secret"},
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["has_credentials"] is True
    assert "credentials" not in body

    updated = client.patch(
        f"/api/v1/suppliers/{body['id']}",
        json={"version": 1, "name": "改名供应商", "status": "inactive"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "改名供应商"
    assert updated.json()["status"] == "inactive"

    stale = client.patch(
        f"/api/v1/suppliers/{body['id']}", json={"version": 1, "name": "x"}, headers=headers
    )
    assert stale.status_code == 409


def test_list_suppliers(client):
    headers = auth_headers(client)
    client.post("/api/v1/suppliers", json={"name": "A"}, headers=headers)
    client.post("/api/v1/suppliers", json={"name": "B"}, headers=headers)
    listed = client.get("/api/v1/suppliers", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2
