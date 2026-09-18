"""Unit tests for TickerTapeClient and sub-resources."""

import json
from pathlib import Path
import pytest
import respx
import httpx

from folioman_intelligence.clients.tickertape.client import TickerTapeClient
from folioman_intelligence.clients.tickertape.constants import BASE_URL, SITEMAP_URLS
from folioman_intelligence.clients.tickertape.errors import (
    TickerTapeHTTPError,
    TickerTapeNotFoundError,
)

SAMPLE_URLSET_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://www.tickertape.in/mutualfunds/quant-active-fund-M_ESAF</loc>
        <lastmod>2026-03-01</lastmod>
    </url>
</urlset>
"""

SAMPLE_JSON_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "folioman_intelligence"
    / "clients"
    / "tickertape"
    / "sample_mf_parser_response.json"
)


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "tickertape_cache"


@pytest.mark.asyncio
async def test_client_context_manager(temp_cache_dir: Path):
    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        assert client.base_url == BASE_URL
        assert not client._http_client.is_closed
    assert client._http_client.is_closed


@pytest.mark.asyncio
@respx.mock
async def test_client_http_errors(temp_cache_dir: Path):
    respx.get(f"{BASE_URL}/not-found").mock(return_value=httpx.Response(404, text="Not Found"))
    respx.get(f"{BASE_URL}/server-error").mock(return_value=httpx.Response(500, text="Internal Error"))

    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        with pytest.raises(TickerTapeNotFoundError) as exc_404:
            await client.request("GET", "/not-found")
        assert exc_404.value.status_code == 404

        with pytest.raises(TickerTapeHTTPError) as exc_500:
            await client.request("GET", "/server-error")
        assert exc_500.value.status_code == 500


@pytest.mark.asyncio
@respx.mock
async def test_sitemap_caching_and_refresh_behavior(temp_cache_dir: Path):
    sitemap_route = respx.get(SITEMAP_URLS["mf"]).mock(
        return_value=httpx.Response(200, text=SAMPLE_URLSET_XML)
    )

    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        # Cache initially empty
        assert not client.sitemap.is_cached("mf")

        # 1. First get() should make live network request and populate cache
        items = await client.sitemap.get("mf")
        assert len(items) == 1
        assert items[0].record_id == "M_ESAF"
        assert sitemap_route.call_count == 1
        assert client.sitemap.is_cached("mf")

        # 2. Second get() with force_refresh=False should serve from disk cache (NO network call)
        cached_items = await client.sitemap.get("mf", force_refresh=False)
        assert len(cached_items) == 1
        assert cached_items[0].record_id == "M_ESAF"
        assert sitemap_route.call_count == 1  # Route not called again!

        # 3. Third get() with force_refresh=True should hit network and update cache
        refreshed_items = await client.sitemap.get("mf", force_refresh=True)
        assert len(refreshed_items) == 1
        assert sitemap_route.call_count == 2

        # 4. Explicit refresh() should hit network
        explicit_refreshed = await client.sitemap.refresh("mf")
        assert len(explicit_refreshed) == 1
        assert sitemap_route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_mf_resource_get_and_get_isin(temp_cache_dir: Path):
    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    html_payload = f"""
    <html>
      <head></head>
      <body>
        <script id="__NEXT_DATA__" type="application/json">
          {json.dumps(sample_data)}
        </script>
      </body>
    </html>
    """

    respx.get(f"{BASE_URL}/mutualfunds/quant-infrastructure-fund-M_QUNG").mock(
        return_value=httpx.Response(200, text=html_payload)
    )

    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        # Test full fund retrieval
        fund = await client.mf.get("quant-infrastructure-fund-M_QUNG")
        assert fund.mf_id == "M_QUNG"
        assert fund.isin == "INF966L01721"
        assert fund.name == "Quant Infrastructure Fund"
        assert fund.nav == 45.0937

        # Test convenience ISIN getter
        isin = await client.mf.get_isin("quant-infrastructure-fund-M_QUNG")
        assert isin == "INF966L01721"

        # Test get_raw
        raw = await client.mf.get_raw("quant-infrastructure-fund-M_QUNG")
        assert "props" in raw


@pytest.mark.asyncio
@respx.mock
async def test_sitemap_get_references(temp_cache_dir: Path):
    index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://www.tickertape.in/sitemaps/mutualfunds/sitemap-1.xml</loc>
            <lastmod>2026-03-01</lastmod>
        </sitemap>
    </sitemapindex>
    """
    respx.get("https://example.com/index.xml").mock(return_value=httpx.Response(200, text=index_xml))

    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        refs = await client.sitemap.get_references("https://example.com/index.xml")
        assert len(refs) == 1
        assert refs[0].url == "https://www.tickertape.in/sitemaps/mutualfunds/sitemap-1.xml"

        # Clear cache test
        client.sitemap.clear_cache()


@pytest.mark.asyncio
async def test_sitemap_unknown_category(temp_cache_dir: Path):
    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        with pytest.raises(ValueError, match="Unknown sitemap category 'unknown'"):
            await client.sitemap.get("unknown")

