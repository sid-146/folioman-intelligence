# TickerTape Client & Market Scraper

The `TickerTapeClient` is an asynchronous web client and scraping engine designed to collect mutual fund data, financial ratios, stock holdings, scorecard ratings, and sector allocations from [TickerTape.in](https://www.tickertape.in).

It includes an on-disk sitemap cache and a persistent SQLite lookup database (`isin_lookup.db`) that maps Indian mutual fund ISINs directly to TickerTape entities and categories.

---

## Architectural Workflow

```
                        [ TickerTapeClient ]
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[ SitemapResource ]                             [ MutualFundsResource ]
  - XML Sitemap Parser                            - Next.js __NEXT_DATA__ Scraper
  - Disk Cache (.cache/sitemaps/)                 - MFParser (BeautifulSoup)
         │                                                 │
         └────────────────────────┬────────────────────────┘
                                  ▼
                    [ SQLite ISIN Lookup System ]
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
    [ ISINLookupTable ]    [ ISINResolver ]      [ ISINIndexer ]
    (Persistent SQLite)    (On-demand Match)     (Bulk Sitemap Crawler)
```

---

## Client Initialization

```python
from pathlib import Path
from folioman_intelligence import TickerTapeClient

async with TickerTapeClient(
    base_url="https://www.tickertape.in",
    timeout=30.0,
    cache_dir=Path(".cache/tickertape"),
) as client:
    # Client operations
    ...
```

### Constructor Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `base_url` | `str` | `https://www.tickertape.in` | TickerTape base URL. |
| `timeout` | `float` | `30.0` | HTTP request timeout in seconds. |
| `cache_dir` | `Path \| str` | `.cache/tickertape` | Local directory for storing sitemap JSON files and the SQLite lookup database. |
| `http_client` | `httpx.AsyncClient \| None` | `None` | Optional custom HTTP client. |
| `headers` | `dict[str, str] \| None` | `None` | Additional HTTP headers. Uses browser user-agent by default. |
| `sitemap_urls` | `dict[str, str] \| None` | Default sitemaps | Custom dictionary of sitemap URLs. |

---

## Sitemap Ingestion & Disk Caching (`client.sitemap`)

TickerTape exposes large XML sitemaps containing URLs for all listed mutual funds, stocks, and ETFs. The client downloads, parses, and caches these locally to avoid unnecessary network calls.

### Available Sitemaps

| Category Key | Target Endpoint |
| :--- | :--- |
| `"mf"` | `https://www.tickertape.in/sitemaps/mutualfunds/sitemap.xml` |
| `"stocks"` | `https://www.tickertape.in/sitemaps/stocks/sitemap.xml` |
| `"etf"` | `https://www.tickertape.in/sitemaps/etfs/sitemap.xml` |
| `"us-stocks"` | `https://www.tickertape.in/sitemaps/us-stocks/sitemap.xml` |
| `"us-etf"` | `https://www.tickertape.in/sitemaps/us-etfs/sitemap.xml` |

### Methods

#### `get(category, force_refresh=False)`
```python
async def get(
    self,
    category: str = "mf",
    *,
    force_refresh: bool = False,
) -> list[SitemapURL]
```
Returns parsed sitemap entries from local cache (`.cache/tickertape/sitemaps/{category}.json`). If the cache does not exist or `force_refresh=True`, it fetches the live XML and updates the cache.

#### `refresh(category)`
```python
async def refresh(self, category: str = "mf") -> list[SitemapURL]
```
Forces a live fetch of the sitemap XML and overwrites the local cache.

---

## Mutual Funds Resource (`client.mf`)

Handles page fetching, hydration payload parsing, and direct ISIN resolution.

### Methods

#### `get(slug_or_mfid)`
```python
async def get(self, slug_or_mfid: str) -> MutualFundDetail
```
Fetches and parses a mutual fund page by slug (e.g. `"quant-infrastructure-fund-M_QUNG"`) or MFID (`"M_QUNG"`).
- **Extraction Mechanism**: Parses the HTML with `BeautifulSoup`, extracts the `<script id="__NEXT_DATA__">` JSON block, and constructs a `MutualFundDetail` model.
- **Returns**: `MutualFundDetail`

#### `get_by_isin(isin, hint_name=None)`
```python
async def get_by_isin(
    self,
    isin: str,
    hint_name: str | None = None,
) -> MutualFundDetail | None
```
Resolves a 12-character Indian ISIN (e.g. `"INF966L01721"`) from Folioman into full TickerTape details.
- Checks local SQLite lookup table first.
- If not indexed, uses `hint_name` to search sitemap slugs, verifies candidate pages, and saves the verified match into SQLite.
- **Returns**: `MutualFundDetail` or `None`.

#### `get_peers(isin, match_plan=True, match_option=True, limit=20)`
```python
def get_peers(
    self,
    isin: str,
    match_plan: bool = True,
    match_option: bool = True,
    limit: int = 20,
) -> list[ISINMapping]
```
Finds peer mutual funds in the same subsector/category from the local SQLite database.

#### `find_funds(...)`
```python
def find_funds(
    self,
    *,
    sector: str | None = None,
    subsector: str | None = None,
    fund_type: str | None = None,
    plan: str | None = None,
    option: str | None = None,
    risk_level: str | None = None,
    benchmark: str | None = None,
    amc: str | None = None,
    limit: int = 100,
) -> list[ISINMapping]
```
Filters indexed mutual funds using classification attributes.

#### `build_isin_index(...)`
```python
async def build_isin_index(
    self,
    *,
    force_refresh: bool = False,
    concurrency: int = 5,
    delay: float = 0.5,
    limit: int | None = None,
    progress_callback: Callable[[int, int, int, int], None] | None = None,
) -> int
```
Crawls sitemap URLs and populates the SQLite database. Supports rate-limited concurrency and progress reporting.

---

## SQLite Persistent ISIN Lookup Table

Located at `.cache/tickertape/isin_lookup.db`.

### Database Schema (`mf_isin_lookup`)

| Column Name | SQL Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `isin` | `TEXT` | `PRIMARY KEY` | 12-character Indian ISIN code. |
| `record_id` | `TEXT` | `NOT NULL` | TickerTape record ID (e.g. `M_QUNG`). |
| `slug` | `TEXT` | `NOT NULL` | URL slug path. |
| `name` | `TEXT` | `NOT NULL` | Scheme name. |
| `amc` | `TEXT` | | Asset Management Company (e.g. `Quant`). |
| `amc_code` | `TEXT` | | AMC code identifier. |
| `sector` | `TEXT` | Indexed | Primary asset class (e.g. `Equity`). |
| `subsector` | `TEXT` | Indexed | Category (e.g. `Sectoral Fund - Infrastructure`). |
| `fund_type` | `TEXT` | | Classification (e.g. `Equity`). |
| `fund_class` | `TEXT` | | Scheme type (e.g. `Open`). |
| `plan` | `TEXT` | | `"Direct"` or `"Regular"`. |
| `option` | `TEXT` | | `"Growth"` or `"IDCW"`. |
| `risk_level` | `TEXT` | | SEBI risk rating (e.g. `"Very High"`). |
| `benchmark` | `TEXT` | Indexed | Target benchmark index. |
| `url` | `TEXT` | `NOT NULL` | Full TickerTape page URL. |
| `nav` | `REAL` | | Latest closing NAV. |
| `updated_at` | `TEXT` | `NOT NULL` | UTC ISO-8601 timestamp. |

### Table Management Methods (`ISINLookupTable`)

```python
table = client.mf.lookup

# Fetch single mapping
mapping = table.get("INF966L01721")

# Batch fetch
mappings_dict = table.get_batch(["INF966L01721", "INF846K01EW2"])

# Get total count of indexed funds
total = table.count()

# Export database
table.export_json("exports/funds.json")
table.export_csv("exports/funds.csv")
```

---

## Heuristic ISIN Resolver (`ISINResolver`)

When an ISIN is not yet in the SQLite database, `ISINResolver.resolve(isin, hint_name)` matches it dynamically:

1. **Token Extraction**: Extracts alphanumeric words from `hint_name`, excluding stop words (`"fund"`, `"growth"`, `"direct"`, `"equity"`).
2. **Slug Scoring**: Computes token overlap across all mutual fund sitemap URLs.
3. **Candidate Verification**: Fetches the top 3 highest-scoring page payloads and checks if the page `isin` matches.
4. **Auto-Persist**: Upon a verified match, inserts the record into SQLite for instant future lookups.

---

## Data Models

### `MutualFundDetail`
Top-level representation of scraped mutual fund data:
- `mf_id: str`: TickerTape fund ID.
- `name: str`: Scheme name.
- `isin: str | None`: ISIN code.
- `slug: str | None`: Page slug.
- `nav: float | None`: Latest NAV price.
- `security_info: MFSecurityInfo | None`: Amc, option, sector, 1-day NAV change.
- `meta: MFMeta | None`: Detailed metadata, AUM, expense ratio, benchmark, risk rating.
- `scorecard: list[MFScorecardItem]`: Scorecard ratings for Performance, Risk, Cost, etc.
- `raw_props: dict[str, Any] | None`: Raw Next.js `pageProps` dictionary.

### `ISINMapping`
Flattened entity stored in the SQLite database:
- `isin: str`, `record_id: str`, `slug: str`, `name: str`, `amc: str | None`, `sector: str | None`, `subsector: str | None`, `plan: str | None`, `option: str | None`, `benchmark: str | None`, `nav: float | None`, `updated_at: str`.

---

## Error Handling

```
TickerTapeError (base exception)
├── TickerTapeHTTPError (status_code, response_data)
│   └── TickerTapeNotFoundError (HTTP 404)
└── TickerTapeParseError (failed to find or parse __NEXT_DATA__ or XML)
```
