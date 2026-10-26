"""Demo collector for books.toscrape.com — a sandbox explicitly published
for scraping practice (its homepage literally says "We love being
scraped!"), used here to demonstrate the HTTP_STATIC collection method end
to end against known, stable, real markup. Selectors below match that
site's actual HTML structure (class names like `product_pod`,
`price_color`, `instock availability`, the `table.table-striped` product
info table) — this is not a made-up schema.

This is a template for how a real supplier's collector should be
structured, not a supplier this project actually sells from. Swapping in a
real supplier means: new subclass, new selectors matched to that
supplier's real HTML, same base class and same CollectedProduct shape."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.collectors.http_static import CollectedProduct, HttpStaticCollector

PRICE_RE = re.compile(r"[\d.]+")


class BooksToScrapeCollector(HttpStaticCollector):
    request_delay_seconds = 0.3  # books.toscrape.com is a low-traffic sandbox; still polite, not aggressive

    def parse_listing_page(self, soup: BeautifulSoup, page_url: str) -> list[str]:
        urls = []
        for article in soup.select("article.product_pod"):
            link = article.select_one("h3 a")
            if link and link.get("href"):
                urls.append(urljoin(page_url, link["href"]))
        return urls

    def next_page_url(self, soup: BeautifulSoup, current_url: str) -> str | None:
        next_link = soup.select_one("li.next a")
        if next_link and next_link.get("href"):
            return urljoin(current_url, next_link["href"])
        return None

    def parse_detail_page(self, soup: BeautifulSoup, page_url: str) -> CollectedProduct:
        title_el = soup.select_one("div.product_main h1")
        title = title_el.get_text(strip=True) if title_el else ""

        price_el = soup.select_one("div.product_main p.price_color")
        price_text = price_el.get_text(strip=True) if price_el else "0"
        price_match = PRICE_RE.search(price_text)
        price = price_match.group(0) if price_match else "0"

        availability_el = soup.select_one("p.instock.availability")
        availability_text = availability_el.get_text(strip=True) if availability_el else ""
        in_stock = "in stock" in availability_text.lower()

        description_el = soup.select_one("#product_description ~ p")
        description = description_el.get_text(strip=True) if description_el else ""

        breadcrumb_items = soup.select("ul.breadcrumb li a")
        # breadcrumb is Home > Books > <Category> > title; category is the
        # last link before the current (non-link) page.
        category = breadcrumb_items[-1].get_text(strip=True) if len(breadcrumb_items) >= 3 else ""

        image_el = soup.select_one("div.item.active img")
        image_urls = [urljoin(page_url, image_el["src"])] if image_el and image_el.get("src") else []

        sku = ""
        upc = ""
        for row in soup.select("table.table.table-striped tr"):
            header = row.select_one("th")
            value = row.select_one("td")
            if not header or not value:
                continue
            label = header.get_text(strip=True)
            if label == "UPC":
                upc = value.get_text(strip=True)
                sku = upc

        return CollectedProduct(
            source_url=page_url,
            title=title,
            price=price,
            currency="GBP",
            category=category,
            sku=sku,
            description=description,
            image_urls=image_urls,
            in_stock=in_stock,
            raw={"upc": upc, "availability_text": availability_text},
        )
