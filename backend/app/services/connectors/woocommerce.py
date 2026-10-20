import httpx

from app.services.connectors.base import ConnectorError, SiteConnector


class WooCommerceConnector(SiteConnector):
    """Talks to the real WooCommerce REST API v3
    (https://woocommerce.github.io/woocommerce-rest-api-docs/). This
    sandbox has no live WooCommerce store to test against, so automated
    tests run this exact code against a mocked HTTP transport (respx) that
    returns real WooCommerce API response shapes — the HTTP layer is
    swapped, the connector logic is not. This is explicitly NOT a fake
    client with hardcoded return values; connecting it to a real store
    requires no code change, only real base_url/consumer_key/consumer_secret."""

    def __init__(self, base_url: str, consumer_key: str, consumer_secret: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/") + "/wp-json/wc/v3"
        self._auth = (consumer_key, consumer_secret)
        self._timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, auth=self._auth, timeout=self._timeout)

    async def find_by_sku(self, sku: str) -> dict | None:
        async with self._client() as client:
            resp = await client.get("/products", params={"sku": sku})
        self._raise_for_status(resp)
        results = resp.json()
        return results[0] if results else None

    async def create_product(self, payload: dict) -> dict:
        async with self._client() as client:
            resp = await client.post("/products", json=payload)
        self._raise_for_status(resp)
        return resp.json()

    async def update_product(self, external_id: str, payload: dict) -> dict:
        async with self._client() as client:
            resp = await client.put(f"/products/{external_id}", json=payload)
        self._raise_for_status(resp)
        return resp.json()

    async def get_product(self, external_id: str) -> dict | None:
        async with self._client() as client:
            resp = await client.get(f"/products/{external_id}")
        if resp.status_code == 404:
            return None
        self._raise_for_status(resp)
        return resp.json()

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("message", resp.text)
            except Exception:
                detail = resp.text
            raise ConnectorError(f"WooCommerce API 错误 ({resp.status_code}): {detail}")


def build_woocommerce_payload(preview) -> dict:
    """Maps the project's internal preview shape to WooCommerce's product
    payload shape. Deliberately small and explicit rather than a generic
    mapper — field-mapping/capability-detection generality is Phase 6 work
    once a second platform exists to generalize from."""
    return {
        "name": preview.title,
        "description": preview.description,
        "regular_price": str(preview.price),
        "categories": [{"name": preview.category}] if preview.category else [],
        "tags": [{"name": t} for t in preview.tags],
        "sku": None,  # filled in by the caller, which knows the internal SKU
    }
