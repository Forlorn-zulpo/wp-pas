import io

from PIL import Image

from tests.helpers import auth_headers


def _make_png_bytes(color=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", (40, 30), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_product(client, headers):
    resp = client.post(
        "/api/v1/products",
        json={"sku": "ASSET-SKU-1", "title": "带图片的商品", "price": "9.99"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_upload_asset_and_fetch_file(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)

    files = {"file": ("photo.png", _make_png_bytes(), "image/png")}
    resp = client.post(f"/api/v1/products/{product['id']}/assets", files=files, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["width"] == 40
    assert body["height"] == 30
    assert body["is_primary"] is True

    fetched = client.get(f"/api/v1/assets/{body['id']}/file", headers=headers)
    assert fetched.status_code == 200
    assert fetched.headers["content-type"] == "image/png"

    detail = client.get(f"/api/v1/products/{product['id']}", headers=headers).json()
    assert len(detail["assets"]) == 1


def test_upload_rejects_non_image(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)

    files = {"file": ("not_an_image.png", b"this is not a real image", "image/png")}
    resp = client.post(f"/api/v1/products/{product['id']}/assets", files=files, headers=headers)
    assert resp.status_code == 422


def test_upload_rejects_disallowed_content_type(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)

    files = {"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")}
    resp = client.post(f"/api/v1/products/{product['id']}/assets", files=files, headers=headers)
    assert resp.status_code == 415


def test_second_upload_is_not_primary_and_can_be_promoted(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)

    first = client.post(
        f"/api/v1/products/{product['id']}/assets",
        files={"file": ("a.png", _make_png_bytes((255, 0, 0)), "image/png")},
        headers=headers,
    ).json()
    second = client.post(
        f"/api/v1/products/{product['id']}/assets",
        files={"file": ("b.png", _make_png_bytes((0, 255, 0)), "image/png")},
        headers=headers,
    ).json()

    assert first["is_primary"] is True
    assert second["is_primary"] is False
    assert second["position"] == 1

    promoted = client.post(f"/api/v1/assets/{second['id']}/primary", headers=headers)
    assert promoted.status_code == 200
    assert promoted.json()["is_primary"] is True

    detail = client.get(f"/api/v1/products/{product['id']}", headers=headers).json()
    primaries = [a for a in detail["assets"] if a["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["id"] == second["id"]


def test_delete_asset(client):
    headers = auth_headers(client)
    product = _create_product(client, headers)
    asset = client.post(
        f"/api/v1/products/{product['id']}/assets",
        files={"file": ("a.png", _make_png_bytes(), "image/png")},
        headers=headers,
    ).json()

    deleted = client.delete(f"/api/v1/assets/{asset['id']}", headers=headers)
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/assets/{asset['id']}/file", headers=headers)
    assert missing.status_code == 404
