"""AI config CRUD is tested normally. The actual generation call
(test_generate_title_*) mocks the Anthropic HTTP endpoint via respx, since
this sandbox has no real Anthropic API key provisioned for the project's
own use — see AnthropicClient's docstring."""

import respx
from httpx import Response

from tests.helpers import auth_headers


def _setup_provider_model_policy(client, headers, provider_type="anthropic"):
    provider = client.post(
        "/api/v1/ai/providers",
        json={"name": "测试Provider", "provider_type": provider_type, "api_key": "sk-test-key"},
        headers=headers,
    ).json()
    model = client.post(
        "/api/v1/ai/models",
        json={
            "provider_id": provider["id"], "model_id": "claude-haiku-5-5", "display_name": "Haiku",
            "input_cost_per_1k_tokens": "0.001", "output_cost_per_1k_tokens": "0.005",
        },
        headers=headers,
    ).json()
    policy = client.post(
        "/api/v1/ai/task-policies",
        json={"task_type": "title_generation", "model_id": model["id"], "max_tokens": 100},
        headers=headers,
    ).json()
    return provider, model, policy


def test_provider_never_exposes_api_key(client):
    headers = auth_headers(client)
    provider, _, _ = _setup_provider_model_policy(client, headers)
    assert provider["has_api_key"] is True
    assert "api_key" not in provider


def test_duplicate_task_policy_rejected(client):
    headers = auth_headers(client)
    _, model, _ = _setup_provider_model_policy(client, headers)
    dup = client.post(
        "/api/v1/ai/task-policies",
        json={"task_type": "title_generation", "model_id": model["id"]},
        headers=headers,
    )
    assert dup.status_code == 409


def test_task_policy_rejects_model_without_declared_vision_capability(client):
    headers = auth_headers(client)
    _, model, _ = _setup_provider_model_policy(client, headers)
    resp = client.post(
        "/api/v1/ai/task-policies",
        json={"task_type": "image_analysis", "model_id": model["id"]},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "视觉" in resp.json()["error"]["message"]


def test_generate_title_success_and_usage_logged(client):
    headers = auth_headers(client)
    _setup_provider_model_policy(client, headers)
    product = client.post(
        "/api/v1/products",
        json={"sku": "AI-SKU-1", "title": "旧标题", "price": "10", "category": "数码"},
        headers=headers,
    ).json()

    with respx.mock(base_url="https://api.anthropic.com") as mock:
        mock.post("/v1/messages").respond(
            200,
            json={
                "content": [{"type": "text", "text": "全新AI生成的商品标题"}],
                "usage": {"input_tokens": 120, "output_tokens": 15},
            },
        )
        resp = client.post(f"/api/v1/products/{product['id']}/ai/generate-title", headers=headers)

    assert resp.status_code == 200, resp.text
    assert resp.json()["suggested_title"] == "全新AI生成的商品标题"

    # Generation must NOT have modified the product itself.
    unchanged = client.get(f"/api/v1/products/{product['id']}", headers=headers).json()
    assert unchanged["title"] == "旧标题"

    usage = client.get("/api/v1/ai/usage/summary", headers=headers).json()
    title_gen = next(u for u in usage if u["task_type"] == "title_generation")
    assert title_gen["call_count"] == 1
    assert title_gen["total_input_tokens"] == 120
    assert title_gen["total_output_tokens"] == 15
    assert float(title_gen["total_cost"]) > 0


def test_generate_title_without_policy_returns_clear_error(client):
    headers = auth_headers(client)
    product = client.post(
        "/api/v1/products", json={"sku": "NO-POLICY", "title": "x", "price": "1"}, headers=headers
    ).json()
    resp = client.post(f"/api/v1/products/{product['id']}/ai/generate-title", headers=headers)
    assert resp.status_code == 422
    assert "未配置" in resp.json()["error"]["message"]


def test_generate_title_api_failure_is_logged_and_reported(client):
    headers = auth_headers(client)
    _setup_provider_model_policy(client, headers)
    product = client.post(
        "/api/v1/products", json={"sku": "AI-FAIL", "title": "x", "price": "1"}, headers=headers
    ).json()

    with respx.mock(base_url="https://api.anthropic.com") as mock:
        mock.post("/v1/messages").respond(
            401, json={"error": {"message": "invalid x-api-key"}}
        )
        resp = client.post(f"/api/v1/products/{product['id']}/ai/generate-title", headers=headers)

    assert resp.status_code == 422
    assert "401" in resp.json()["error"]["message"]

    usage = client.get("/api/v1/ai/usage/summary", headers=headers).json()
    # A failed call still shows up: cost/usage tracking must not silently
    # drop failures (the project requires failure logging too).
    assert any(u["task_type"] == "title_generation" for u in usage)
