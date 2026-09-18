"""Unit tests for ISIN to TickerTape lookup table, resolver, and indexer."""

import json
from pathlib import Path
import pytest
import respx
import httpx

from folioman_intelligence.clients.tickertape.client import TickerTapeClient
from folioman_intelligence.clients.tickertape.constants import BASE_URL, SITEMAP_URLS
from folioman_intelligence.clients.tickertape.lookup.indexer import ISINIndexer
from folioman_intelligence.clients.tickertape.lookup.models import ISINMapping
from folioman_intelligence.clients.tickertape.lookup.resolver import ISINResolver
from folioman_intelligence.clients.tickertape.lookup.table import ISINLookupTable

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


@pytest.fixture
def lookup_table(temp_cache_dir: Path) -> ISINLookupTable:
    return ISINLookupTable(cache_dir=temp_cache_dir)


def test_lookup_table_crud(lookup_table: ISINLookupTable):
    assert lookup_table.count() == 0

    mapping1 = ISINMapping(
        isin="INF966L01721",
        record_id="M_QUNG",
        slug="quant-infrastructure-fund-M_QUNG",
        name="Quant Infrastructure Fund",
        amc="Quant Money Managers Limited",
        plan="Direct",
        option="Growth",
        url="https://www.tickertape.in/mutualfunds/quant-infrastructure-fund-M_QUNG",
        nav=45.09,
    )
    lookup_table.upsert(mapping1)
    assert lookup_table.count() == 1

    # Fetch by ISIN (case-insensitive)
    found = lookup_table.get("inf966l01721")
    assert found is not None
    assert found.isin == "INF966L01721"
    assert found.record_id == "M_QUNG"
    assert found.nav == 45.09

    # Fetch by record_id
    by_rec = lookup_table.get_by_record_id("M_QUNG")
    assert by_rec is not None
    assert by_rec.isin == "INF966L01721"

    # Fetch non-existent
    assert lookup_table.get("NONEXISTENT") is None

    # Batch fetch
    mapping2 = ISINMapping(
        isin="INF209K01157",
        record_id="M_ABSL",
        slug="aditya-birla-fund-M_ABSL",
        name="Aditya Birla Fund",
        url="https://www.tickertape.in/mutualfunds/aditya-birla-fund-M_ABSL",
    )
    lookup_table.upsert(mapping2)
    assert lookup_table.count() == 2

    batch_res = lookup_table.get_batch(["INF966L01721", "INF209K01157", "UNKNOWN"])
    assert len(batch_res) == 2
    assert "INF966L01721" in batch_res
    assert "INF209K01157" in batch_res

    # Sets
    assert lookup_table.get_all_record_ids() == {"M_QUNG", "M_ABSL"}
    assert lookup_table.get_all_isins() == {"INF966L01721", "INF209K01157"}

    # Clear
    lookup_table.clear()
    assert lookup_table.count() == 0


def test_lookup_table_exports(lookup_table: ISINLookupTable, tmp_path: Path):
    mapping = ISINMapping(
        isin="INF966L01721",
        record_id="M_QUNG",
        slug="quant-infrastructure-fund-M_QUNG",
        name="Quant Infrastructure Fund",
        url="https://www.tickertape.in/mutualfunds/quant-infrastructure-fund-M_QUNG",
    )
    lookup_table.upsert(mapping)

    json_path = tmp_path / "export.json"
    lookup_table.export_json(json_path)
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["isin"] == "INF966L01721"

    csv_path = tmp_path / "export.csv"
    lookup_table.export_csv(csv_path)
    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    assert "INF966L01721" in content


@pytest.mark.asyncio
@respx.mock
async def test_targeted_resolver(temp_cache_dir: Path):
    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    html_payload = f"""
    <html><body>
      <script id="__NEXT_DATA__" type="application/json">{json.dumps(sample_data)}</script>
    </body></html>
    """

    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://www.tickertape.in/mutualfunds/sbi-bluechip-fund-M_SBIB</loc></url>
        <url><loc>https://www.tickertape.in/mutualfunds/quant-infrastructure-fund-M_QUNG</loc></url>
    </urlset>
    """

    respx.get(SITEMAP_URLS["mf"]).mock(
        return_value=httpx.Response(200, text=sitemap_xml)
    )
    respx.get(f"{BASE_URL}/mutualfunds/quant-infrastructure-fund-M_QUNG").mock(
        return_value=httpx.Response(200, text=html_payload)
    )

    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        resolver = ISINResolver(client)

        # Resolve using ISIN and hint name
        mapping = await resolver.resolve(
            isin="INF966L01721",
            hint_name="Quant Infrastructure Fund - Growth - Direct Plan",
        )
        assert mapping is not None
        assert mapping.isin == "INF966L01721"
        assert mapping.record_id == "M_QUNG"

        # Check that it got saved in the SQLite table
        table = ISINLookupTable(cache_dir=temp_cache_dir)
        cached_mapping = table.get("INF966L01721")
        assert cached_mapping is not None
        assert cached_mapping.slug == "quant-infrastructure-fund-M_QUNG"


@pytest.mark.asyncio
@respx.mock
async def test_indexer_with_force_refresh_logic(temp_cache_dir: Path):
    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    html_payload = f"""
    <html><body>
      <script id="__NEXT_DATA__" type="application/json">{json.dumps(sample_data)}</script>
    </body></html>
    """

    sitemap_v1 = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://www.tickertape.in/mutualfunds/quant-infrastructure-fund-M_QUNG</loc></url>
    </urlset>
    """

    sitemap_v2 = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://www.tickertape.in/mutualfunds/quant-infrastructure-fund-M_QUNG</loc></url>
        <url><loc>https://www.tickertape.in/mutualfunds/quant-active-fund-M_ESAF</loc></url>
    </urlset>
    """

    sitemap_route = respx.get(SITEMAP_URLS["mf"]).mock(
        return_value=httpx.Response(200, text=sitemap_v1)
    )
    fund_route = respx.get(
        f"{BASE_URL}/mutualfunds/quant-infrastructure-fund-M_QUNG"
    ).mock(return_value=httpx.Response(200, text=html_payload))

    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        # 1. Initial indexing
        indexed_count = await client.mf.build_isin_index(concurrency=2)
        assert indexed_count == 1
        assert client.mf.lookup.count() == 1
        assert sitemap_route.call_count == 1
        assert fund_route.call_count == 1

        # 2. Running again without force_refresh: should skip existing record_id and do NO work
        indexed_again = await client.mf.build_isin_index(force_refresh=False)
        assert indexed_again == 0
        assert sitemap_route.call_count == 1  # Sitemap read from cache!
        assert fund_route.call_count == 1  # Fund page not requested again!

        # 3. Force refresh logic:
        # Update mock route to sitemap_v2
        sitemap_route.mock(return_value=httpx.Response(200, text=sitemap_v2))
        respx.get(f"{BASE_URL}/mutualfunds/quant-active-fund-M_ESAF").mock(
            return_value=httpx.Response(
                200, text=html_payload
            )  # Returns sample payload
        )

        refreshed_count = await client.mf.build_isin_index(force_refresh=True)
        # Should hit sitemap endpoint again (call_count == 2) and update sitemap cache and SQLite
        assert sitemap_route.call_count == 2
        assert refreshed_count >= 1
        assert client.mf.lookup.count() >= 1


@pytest.mark.asyncio
@respx.mock
async def test_client_get_by_isin(temp_cache_dir: Path):
    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        sample_data = json.load(f)

    html_payload = f"""
    <html><body>
      <script id="__NEXT_DATA__" type="application/json">{json.dumps(sample_data)}</script>
    </body></html>
    """

    respx.get(f"{BASE_URL}/mutualfunds/quant-infrastructure-fund-M_QUNG").mock(
        return_value=httpx.Response(200, text=html_payload)
    )

    async with TickerTapeClient(cache_dir=temp_cache_dir) as client:
        # Pre-seed mapping in SQLite
        mapping = ISINMapping(
            isin="INF966L01721",
            record_id="M_QUNG",
            slug="quant-infrastructure-fund-M_QUNG",
            name="Quant Infrastructure Fund",
            url="https://www.tickertape.in/mutualfunds/quant-infrastructure-fund-M_QUNG",
        )
        client.mf.lookup.upsert(mapping)

        # Call get_by_isin
        fund = await client.mf.get_by_isin("INF966L01721")
        assert fund is not None
        assert fund.isin == "INF966L01721"
        assert fund.mf_id == "M_QUNG"
        assert fund.name == "Quant Infrastructure Fund"
