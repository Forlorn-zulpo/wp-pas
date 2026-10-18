from tests.helpers import auth_headers


def _upload_csv(client, headers, content: str, filename="products.csv"):
    files = {"file": (filename, content.encode("utf-8"), "text/csv")}
    return client.post("/api/v1/imports", files=files, headers=headers)


def test_import_valid_csv_creates_products(client):
    headers = auth_headers(client)
    csv_content = (
        "sku,title,price,category\n"
        "IMP-1,导入商品一,12.50,鞋类\n"
        "IMP-2,导入商品二,8.00,服装\n"
    )
    resp = _upload_csv(client, headers, csv_content)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["total_rows"] == 2
    assert body["success_rows"] == 2
    assert body["error_rows"] == 0

    listed = client.get("/api/v1/products?search=导入商品", headers=headers).json()
    assert listed["total"] == 2


def test_import_reports_row_level_errors_without_failing_whole_file(client):
    headers = auth_headers(client)
    csv_content = (
        "sku,title,price\n"
        "GOOD-1,正常商品,9.99\n"
        ",缺少SKU商品,5.00\n"
        "GOOD-2,另一个正常商品,not_a_number\n"
    )
    resp = _upload_csv(client, headers, csv_content)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed_with_errors"
    assert body["total_rows"] == 3
    assert body["success_rows"] == 1
    assert body["error_rows"] == 2
    assert len(body["errors"]) == 2


def test_import_rejects_missing_required_columns(client):
    headers = auth_headers(client)
    resp = _upload_csv(client, headers, "name,amount\nfoo,1\n")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed"
    assert "缺少必需列" in body["errors"][0]["message"]


def test_import_duplicate_sku_against_existing_product_is_reported(client):
    headers = auth_headers(client)
    client.post(
        "/api/v1/products", json={"sku": "DUP-1", "title": "已有商品", "price": "1"}, headers=headers
    )
    resp = _upload_csv(client, headers, "sku,title,price\nDUP-1,重复商品,2\n")
    body = resp.json()
    assert body["success_rows"] == 0
    assert body["error_rows"] == 1
    assert "已存在" in body["errors"][0]["message"]


def test_import_rejects_non_csv_file(client):
    headers = auth_headers(client)
    files = {"file": ("data.txt", b"sku,title,price\nA,B,1\n", "text/plain")}
    resp = client.post("/api/v1/imports", files=files, headers=headers)
    assert resp.status_code == 415


def test_list_and_get_import_job(client):
    headers = auth_headers(client)
    created = _upload_csv(client, headers, "sku,title,price\nL-1,列表测试,1\n").json()

    listed = client.get("/api/v1/imports", headers=headers)
    assert listed.status_code == 200
    assert any(j["id"] == created["id"] for j in listed.json())

    fetched = client.get(f"/api/v1/imports/{created['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["filename"] == "products.csv"
