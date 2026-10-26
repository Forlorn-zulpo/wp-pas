"""Unit tests for the collector parsing logic, run against HTML fixtures
rebuilt from books.toscrape.com's real, stable markup (see the fixtures'
own docstrings and books_toscrape.py's module docstring for how they were
sourced). These test the DETERMINISTIC PARSING LOGIC only — no live HTTP
request is made, because this sandbox's network egress doesn't allow
reaching arbitrary websites (see TROUBLESHOOTING.md). When this code runs
on a machine with normal internet access, HttpStaticCollector.fetch() makes
a real httpx request before handing the real HTML to these same parse
functions."""

from pathlib import Path

from bs4 import BeautifulSoup

from app.services.collectors.books_toscrape import BooksToScrapeCollector

FIXTURES = Path(__file__).parent / "fixtures"


def _soup(filename: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / filename).read_text(encoding="utf-8"), "html.parser")


def test_parse_listing_page_extracts_detail_urls():
    collector = BooksToScrapeCollector()
    soup = _soup("books_toscrape_listing.html")
    urls = collector.parse_listing_page(
        soup, "https://books.toscrape.com/catalogue/category/books/suspense_44/index.html"
    )
    assert len(urls) == 1
    assert urls[0].endswith("silence-in-the-dark-logan-point-4_542/index.html")


def test_parse_listing_page_with_multiple_items_and_relative_urls_resolve_correctly():
    collector = BooksToScrapeCollector()
    soup = _soup("books_toscrape_listing_page1_with_next.html")
    urls = collector.parse_listing_page(
        soup, "https://books.toscrape.com/catalogue/category/books/thriller_37/index.html"
    )
    assert len(urls) == 2
    assert urls[0] == "https://books.toscrape.com/catalogue/the-elephant-tree_495/index.html"
    assert urls[1] == "https://books.toscrape.com/catalogue/behind-closed-doors_621/index.html"


def test_next_page_url_detected_when_present():
    collector = BooksToScrapeCollector()
    soup = _soup("books_toscrape_listing_page1_with_next.html")
    next_url = collector.next_page_url(
        soup, "https://books.toscrape.com/catalogue/category/books/thriller_37/index.html"
    )
    assert next_url == "https://books.toscrape.com/catalogue/category/books/thriller_37/page-2.html"


def test_next_page_url_is_none_on_last_page():
    collector = BooksToScrapeCollector()
    soup = _soup("books_toscrape_listing.html")  # only 1 result, no pager
    assert collector.next_page_url(soup, "https://example.com/") is None


def test_parse_detail_page_extracts_real_product_fields():
    """These expected values are the actual data fetched from the live
    books.toscrape.com detail page for this book (title, price, UPC,
    availability, category) — not invented."""
    collector = BooksToScrapeCollector()
    soup = _soup("books_toscrape_detail.html")
    product = collector.parse_detail_page(
        soup, "https://books.toscrape.com/catalogue/silence-in-the-dark-logan-point-4_542/index.html"
    )

    assert product.title == "Silence in the Dark (Logan Point #4)"
    assert product.price == "58.33"
    assert product.currency == "GBP"
    assert product.category == "Suspense"
    assert product.sku == "e46a164cf310fd7d"
    assert product.in_stock is True
    assert "Bailey Adams" in product.description
    assert len(product.image_urls) == 1
    assert product.image_urls[0].endswith("00bf1ae17dde21c66e346dd9c393d6fa.jpg")
    assert product.raw["upc"] == "e46a164cf310fd7d"


def test_parse_detail_page_handles_missing_optional_fields_gracefully():
    """A minimal page missing the description/table must not crash the
    parser — deterministic parsing should degrade to empty fields, not
    raise, since one malformed supplier page must not abort a whole
    collection run (the caller in http_static.py relies on this)."""
    minimal_html = """
    <html><body>
      <div class="product_main">
        <h1>No Description Book</h1>
        <p class="price_color">£10.00</p>
      </div>
    </body></html>
    """
    collector = BooksToScrapeCollector()
    soup = BeautifulSoup(minimal_html, "html.parser")
    product = collector.parse_detail_page(soup, "https://books.toscrape.com/x/index.html")

    assert product.title == "No Description Book"
    assert product.price == "10.00"
    assert product.description == ""
    assert product.sku == ""
    assert product.image_urls == []
    assert product.in_stock is False
