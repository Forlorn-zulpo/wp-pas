class ConnectorError(Exception):
    """Raised for any non-timeout failure talking to the remote platform
    (auth failure, validation error, 5xx that isn't a timeout, etc)."""


class SiteConnector:
    """What every platform connector (WooCommerce now; Shopify/WordPress in
    Phase 6) must implement. The publishing service only talks to this
    interface, never to a specific platform's SDK directly, so adding a new
    platform never touches app/services/publishing.py."""

    async def find_by_sku(self, sku: str) -> dict | None:
        """Look up a remote product by SKU. Used for idempotent creation:
        called before creating a new remote product, and again to
        reconcile after a timeout, so a retry never creates a duplicate."""
        raise NotImplementedError

    async def create_product(self, payload: dict) -> dict:
        """Returns the created remote product (must include 'id')."""
        raise NotImplementedError

    async def update_product(self, external_id: str, payload: dict) -> dict:
        raise NotImplementedError

    async def get_product(self, external_id: str) -> dict | None:
        raise NotImplementedError
