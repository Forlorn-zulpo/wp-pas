import asyncio
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crypto import decrypt_credentials
from app.models.enums import PublicationItemStatus
from app.models.product import Product
from app.models.site import Site
from app.models.site_product import SiteProduct
from app.services.connectors.base import ConnectorError, SiteConnector
from app.services.connectors.woocommerce import WooCommerceConnector, build_woocommerce_payload
from app.services.preview import merge_product_with_override

logger = logging.getLogger("app.publishing")

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0


class PublishResult:
    def __init__(self, success: bool, external_id: str | None = None, error: str = ""):
        self.success = success
        self.external_id = external_id
        self.error = error


def build_connector(site: Site) -> SiteConnector:
    """Platform -> connector lookup. Only WooCommerce is implemented
    (Phase 4 scope); Shopify/WordPress raise clearly rather than silently
    doing nothing, so a misconfigured site fails loudly instead of quietly
    skipping every item in its job."""
    if site.platform.value != "woocommerce":
        raise ConnectorError(
            f"平台 '{site.platform.value}' 暂无可用连接器(当前仅实现 WooCommerce,Phase 6 会补齐其它平台)"
        )
    if not site.encrypted_credentials:
        raise ConnectorError("站点未配置访问凭据")

    creds = decrypt_credentials(site.encrypted_credentials)
    key = creds.get("key") or creds.get("consumer_key")
    secret = creds.get("secret") or creds.get("consumer_secret")
    if not key or not secret:
        raise ConnectorError("站点凭据缺少 consumer key/secret")

    return WooCommerceConnector(base_url=site.base_url, consumer_key=key, consumer_secret=secret)


async def _create_with_reconciliation(connector: SiteConnector, sku: str, payload: dict) -> dict:
    """Implements the project's required reconciliation rule: if creating
    times out, the remote product may or may not have actually been
    created. Before retrying, we query by SKU; if it now exists remotely,
    we adopt that id instead of creating a second one."""
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await connector.create_product(payload)
        except httpx.TimeoutException as exc:
            last_error = exc
            logger.warning("create_product timed out (attempt %d/%d), reconciling by SKU", attempt, MAX_ATTEMPTS)
            existing = await connector.find_by_sku(sku)
            if existing:
                return existing  # it was actually created; don't create a duplicate
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
        except ConnectorError as exc:
            # Not a timeout — a real error (validation, auth, 5xx). Retrying
            # blindly won't help for most of these, but transient 5xXs are
            # common enough on real platforms to warrant limited retries.
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    raise last_error or ConnectorError("创建远端商品失败,原因未知")


async def publish_one(db: AsyncSession, site_product: SiteProduct, site: Site) -> PublishResult:
    """Publishes a single SiteProduct. Always returns a PublishResult rather
    than raising, so one item's failure never aborts the caller's loop over
    the rest of the job — matching the project's requirement that a failure
    on one product must not affect others in the same job."""
    try:
        connector = build_connector(site)
    except ConnectorError as exc:
        return PublishResult(success=False, error=str(exc))

    product = (
        await db.execute(
            select(Product).where(Product.id == site_product.product_id).options(selectinload(Product.assets))
        )
    ).scalar_one_or_none()
    if product is None:
        return PublishResult(success=False, error="内部商品不存在")

    merged = merge_product_with_override(product, site_product.override)
    payload = build_woocommerce_payload(merged)
    payload["sku"] = product.sku

    mapping = site_product.external_mapping

    try:
        if mapping and mapping.external_id:
            # Already published once: this is an update, which is naturally
            # idempotent (PUT with the full desired state), so no
            # reconciliation dance is needed here.
            remote = await connector.update_product(mapping.external_id, payload)
        else:
            # First publish: check for an existing remote product with this
            # SKU before creating, in case an earlier attempt already
            # created it (e.g. a previous job crashed after creating but
            # before saving the mapping).
            existing = await connector.find_by_sku(product.sku)
            remote = existing or await _create_with_reconciliation(connector, product.sku, payload)
    except (ConnectorError, httpx.TimeoutException, httpx.RequestError) as exc:
        return PublishResult(success=False, error=str(exc))

    external_id = str(remote.get("id", ""))
    return PublishResult(success=True, external_id=external_id)
