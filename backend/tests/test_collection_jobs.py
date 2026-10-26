from pathlib import Path

import respx
from httpx import Response

from tests.helpers import auth_headers

FIXTURES = Path(__file__).parent / "fixtures"


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


def test_collection_job_with_registered_collector_actually_runs_and_creates_products(client):
    """End-to-end: create a job naming the "books_toscrape" demo collector,
    with respx standing in for the live HTTP layer (this sandbox can't
    reach books.toscrape.com — see TROUBLESHOOTING.md). The HTML served is
    the exact fixture files whose parsing logic test_collectors.py already
    validated; this test proves the orchestration (create job -> run
    collector -> create draft Products) around that parsing logic actually
    works, not just the parsing in isolation."""
    headers = auth_headers(client)
    supplier = client.post(
        "/api/v1/suppliers",
        json={"name": "Books To Scrape Demo", "website": "https://books.toscrape.com", "collection_method": "http_static"},
        headers=headers,
    ).json()

    listing_html = (FIXTURES / "books_toscrape_listing.html").read_text(encoding="utf-8")
    detail_html = (FIXTURES / "books_toscrape_detail.html").read_text(encoding="utf-8")

    start_url = "https://books.toscrape.com/catalogue/category/books/suspense_44/index.html"
    detail_url = "https://books.toscrape.com/catalogue/silence-in-the-dark-logan-point-4_542/index.html"

    with respx.mock(assert_all_called=False) as mock:
        mock.get(start_url).mock(return_value=Response(200, text=listing_html))
        mock.get(detail_url).mock(return_value=Response(200, text=detail_html))

        resp = client.post(
            "/api/v1/collection-jobs",
            json={
                "supplier_id": supplier["id"],
                "target_config": {"collector": "books_toscrape", "start_url": start_url, "max_pages": 1},
            },
            headers=headers,
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["total_items"] == 1
    assert body["success_items"] == 1
    assert body["error_items"] == 0

    products = client.get("/api/v1/products?search=Silence", headers=headers).json()
    assert products["total"] == 1
    created = products["items"][0]
    assert created["sku"] == "e46a164cf310fd7d"
    assert created["status"] == "draft"  # collected products always start as drafts, never auto-active


def test_collection_job_rerun_skips_already_collected_sku(client):
    """Running the same collection twice must not create duplicate
    products — the SKU dedup check is the same pattern as the CSV import's
    duplicate-SKU handling."""
    headers = auth_headers(client)
    supplier = client.post(
        "/api/v1/suppliers", json={"name": "Dedup Demo", "collection_method": "http_static"}, headers=headers
    ).json()

    listing_html = (FIXTURES / "books_toscrape_listing.html").read_text(encoding="utf-8")
    detail_html = (FIXTURES / "books_toscrape_detail.html").read_text(encoding="utf-8")
    start_url = "https://books.toscrape.com/catalogue/category/books/suspense_44/index.html"
    detail_url = "https://books.toscrape.com/catalogue/silence-in-the-dark-logan-point-4_542/index.html"
    payload = {
        "supplier_id": supplier["id"],
        "target_config": {"collector": "books_toscrape", "start_url": start_url, "max_pages": 1},
    }

    with respx.mock(assert_all_called=False) as mock:
        mock.get(start_url).mock(return_value=Response(200, text=listing_html))
        mock.get(detail_url).mock(return_value=Response(200, text=detail_html))
        first = client.post("/api/v1/collection-jobs", json=payload, headers=headers).json()

    assert first["success_items"] == 1

    with respx.mock(assert_all_called=False) as mock:
        mock.get(start_url).mock(return_value=Response(200, text=listing_html))
        mock.get(detail_url).mock(return_value=Response(200, text=detail_html))
        second = client.post("/api/v1/collection-jobs", json=payload, headers=headers).json()

    assert second["success_items"] == 0
    assert second["error_items"] == 1  # reported as "already exists, skipped"

    products = client.get("/api/v1/products?search=Silence", headers=headers).json()
    assert products["total"] == 1  # still just one — no duplicate


def test_collection_job_total_fetch_failure_marks_job_failed(client):
    """When the very first fetch (the listing page) fails entirely, the
    collector raises CollectorError and the job must be marked FAILED with
    the error recorded — not silently left RUNNING or COMPLETED."""
    headers = auth_headers(client)
    supplier = client.post(
        "/api/v1/suppliers", json={"name": "Total Failure Demo"}, headers=headers
    ).json()
    start_url = "https://books.toscrape.com/catalogue/category/books/nonexistent_999/index.html"

    with respx.mock(assert_all_called=False) as mock:
        mock.get(start_url).mock(return_value=Response(404, text="not found"))
        resp = client.post(
            "/api/v1/collection-jobs",
            json={
                "supplier_id": supplier["id"],
                "target_config": {"collector": "books_toscrape", "start_url": start_url, "max_pages": 1},
            },
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed"
    assert len(body["errors"]) == 1


def test_get_collection_job_not_found(client):
    headers = auth_headers(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/collection-jobs/{fake_id}", headers=headers)
    assert resp.status_code == 404


def test_collection_job_without_registered_collector_stays_pending(client):
    """A target_config that doesn't name a registered collector must not
    silently fake success — it stays PENDING for a human to notice."""
    headers = auth_headers(client)
    supplier = client.post(
        "/api/v1/suppliers", json={"name": "No Collector Yet"}, headers=headers
    ).json()

    resp = client.post(
        "/api/v1/collection-jobs",
        json={"supplier_id": supplier["id"], "target_config": {"notes": "手动录入,暂无抓取器"}},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"
