from tests.helpers import auth_headers


def test_create_collection_job_requires_existing_supplier(client):
    headers = auth_headers(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(
        "/api/v1/collection-jobs", json={"supplier_id": fake_id}, headers=headers
    )
    assert resp.status_code == 404


def test_create_and_list_collection_job_stays_pending(client):
    """No executor is wired up yet (see the endpoint's docstring) — a job
    is created and stays PENDING; this test only verifies the queue
    bookkeeping, not an actual scrape."""
    headers = auth_headers(client)
    supplier = client.post("/api/v1/suppliers", json={"name": "采集测试供应商"}, headers=headers).json()

    job = client.post(
        "/api/v1/collection-jobs",
        json={"supplier_id": supplier["id"], "target_config": {"category_url": "https://example.com/cat"}},
        headers=headers,
    )
    assert job.status_code == 201
    assert job.json()["status"] == "pending"

    listed = client.get("/api/v1/collection-jobs", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
