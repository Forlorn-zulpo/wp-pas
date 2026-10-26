import asyncio
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup


@dataclass
class CollectedProduct:
    """What one parsed product page yields. Deterministic fields only — no
    AI involved in this layer, per the project's rule that AI is for
    genuinely ambiguous data, not for parsing structured HTML."""

    source_url: str
    title: str
    price: str
    currency: str
    category: str
    sku: str
    description: str = ""
    image_urls: list[str] = field(default_factory=list)
    in_stock: bool | None = None
    raw: dict = field(default_factory=dict)


class CollectorError(Exception):
    pass


class HttpStaticCollector:
    """Base class for suppliers whose catalogue is stable server-rendered
    HTML (no JS needed) — the project's collection-strategy default before
    reaching for Playwright. A concrete supplier collector subclasses this
    and implements parse_listing_page/parse_detail_page for that supplier's
    specific markup; everything else (fetching, rate limiting, basic retry)
    is shared here."""

    #: Seconds to wait between requests to the same host — a bare minimum
    #: politeness measure so a collection run doesn't hammer the supplier.
    request_delay_seconds: float = 0.5
    max_retries: int = 2
    timeout_seconds: float = 20.0
    user_agent: str = "ProductOpsAdminBot/1.0 (+collection job; respects robots.txt)"

    async def fetch(self, client: httpx.AsyncClient, url: str) -> BeautifulSoup:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                resp = await client.get(url, headers={"User-Agent": self.user_agent})
                if resp.status_code >= 400:
                    raise CollectorError(f"HTTP {resp.status_code} fetching {url}")
                return BeautifulSoup(resp.text, "html.parser")
            except (httpx.RequestError, CollectorError) as exc:
                last_error = exc
                if attempt <= self.max_retries:
                    await asyncio.sleep(self.request_delay_seconds * attempt)
        raise CollectorError(f"Failed to fetch {url} after {self.max_retries + 1} attempts") from last_error

    def parse_listing_page(self, soup: BeautifulSoup, page_url: str) -> list[str]:
        """Returns the detail-page URLs found on one listing/category page.
        Supplier-specific — override in the subclass."""
        raise NotImplementedError

    def parse_detail_page(self, soup: BeautifulSoup, page_url: str) -> CollectedProduct:
        """Parses one product detail page into a CollectedProduct.
        Supplier-specific — override in the subclass."""
        raise NotImplementedError

    def next_page_url(self, soup: BeautifulSoup, current_url: str) -> str | None:
        """Returns the next listing page's URL, or None if this is the last
        page. Default: no pagination (override for suppliers that paginate)."""
        return None

    async def collect(self, start_url: str, max_pages: int = 10) -> tuple[list[CollectedProduct], list[dict]]:
        """Crawls listing pages starting at start_url (following
        next_page_url up to max_pages), then fetches and parses every
        detail page found. Returns (products, errors): each product's fetch
        failure is caught and recorded rather than aborting the whole run —
        matching the project's "one failure must not block the rest"
        principle, applied here to collection the same way it's applied to
        publishing. This module stays DB-free (no CollectionJob writes
        here) so it can be unit-tested without a database."""
        results: list[CollectedProduct] = []
        errors: list[dict] = []

        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            detail_urls: list[str] = []
            page_url: str | None = start_url
            pages_visited = 0

            while page_url and pages_visited < max_pages:
                soup = await self.fetch(client, page_url)
                detail_urls.extend(self.parse_listing_page(soup, page_url))
                page_url = self.next_page_url(soup, page_url)
                pages_visited += 1
                await asyncio.sleep(self.request_delay_seconds)

            for url in detail_urls:
                try:
                    soup = await self.fetch(client, url)
                    results.append(self.parse_detail_page(soup, url))
                except CollectorError as exc:
                    errors.append({"url": url, "message": str(exc)})
                await asyncio.sleep(self.request_delay_seconds)

        return results, errors
