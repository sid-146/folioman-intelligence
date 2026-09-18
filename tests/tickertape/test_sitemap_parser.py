"""Unit tests for SitemapParser."""

import pytest
from folioman_intelligence.clients.tickertape.errors import TickerTapeParseError
from folioman_intelligence.clients.tickertape.models import SitemapReference, SitemapURL
from folioman_intelligence.clients.tickertape.parsers.sitemap import SitemapParser

SAMPLE_URLSET_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://www.tickertape.in/mutualfunds/quant-active-fund-M_ESAF</loc>
        <lastmod>2026-03-01</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://www.tickertape.in/mutualfunds/sbi-bluechip-fund-M_SBIB</loc>
        <lastmod>2026-03-02</lastmod>
    </url>
</urlset>
"""

SAMPLE_INDEX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://www.tickertape.in/sitemaps/mutualfunds/sitemap-1.xml</loc>
        <lastmod>2026-03-01</lastmod>
    </sitemap>
    <sitemap>
        <loc>https://www.tickertape.in/sitemaps/mutualfunds/sitemap-2.xml</loc>
        <lastmod>2026-03-02</lastmod>
    </sitemap>
</sitemapindex>
"""


def test_parse_urlset():
    parser = SitemapParser(SAMPLE_URLSET_XML)
    results = parser.parse()

    assert len(results) == 2
    assert all(isinstance(r, SitemapURL) for r in results)

    item1 = results[0]
    assert item1.record_id == "M_ESAF"
    assert item1.url == "https://www.tickertape.in/mutualfunds/quant-active-fund-M_ESAF"
    assert item1.last_modified == "2026-03-01"
    assert item1.change_frequency == "daily"
    assert item1.priority == 0.8

    item2 = results[1]
    assert item2.record_id == "M_SBIB"
    assert item2.last_modified == "2026-03-02"
    assert item2.priority is None


def test_parse_sitemap_index():
    parser = SitemapParser(SAMPLE_INDEX_XML)
    results = parser.parse()

    assert len(results) == 2
    assert all(isinstance(r, SitemapReference) for r in results)

    assert (
        results[0].url == "https://www.tickertape.in/sitemaps/mutualfunds/sitemap-1.xml"
    )
    assert results[0].last_modified == "2026-03-01"
    assert (
        results[1].url == "https://www.tickertape.in/sitemaps/mutualfunds/sitemap-2.xml"
    )


def test_parse_invalid_xml():
    parser = SitemapParser("<invalid><xml")
    with pytest.raises(TickerTapeParseError, match="Malformed sitemap XML"):
        parser.parse()


def test_parse_unsupported_root():
    parser = SitemapParser("<unsupported><loc>https://example.com</loc></unsupported>")
    with pytest.raises(TickerTapeParseError, match="Unsupported sitemap root element"):
        parser.parse()


def test_parse_no_content():
    parser = SitemapParser()
    with pytest.raises(TickerTapeParseError, match="No XML content provided"):
        parser.parse()
