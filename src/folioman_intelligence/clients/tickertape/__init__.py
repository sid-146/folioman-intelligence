"""TickerTape Client Package."""

from folioman_intelligence.clients.tickertape.client import TickerTapeClient
from folioman_intelligence.clients.tickertape.constants import (
    BASE_URL,
    DEFAULT_CACHE_DIR,
    DEFAULT_HEADERS,
    SITEMAP_URLS,
    URLS,
)
from folioman_intelligence.clients.tickertape.errors import (
    TickerTapeError,
    TickerTapeHTTPError,
    TickerTapeNotFoundError,
    TickerTapeParseError,
)
from folioman_intelligence.clients.tickertape.models import (
    MFMeta,
    MFScorecardItem,
    MFSecurityInfo,
    MutualFundDetail,
    SitemapCacheData,
    SitemapReference,
    SitemapURL,
)
from folioman_intelligence.clients.tickertape.parsers import (
    BaseParser,
    MFParser,
    SitemapParser,
    get_parser,
    register_parser,
)
from folioman_intelligence.clients.tickertape.storage import SitemapCacheManager

__all__ = [
    "TickerTapeClient",
    "TickerTapeError",
    "TickerTapeHTTPError",
    "TickerTapeNotFoundError",
    "TickerTapeParseError",
    "SitemapURL",
    "SitemapReference",
    "SitemapCacheData",
    "MutualFundDetail",
    "MFSecurityInfo",
    "MFMeta",
    "MFScorecardItem",
    "BaseParser",
    "SitemapParser",
    "MFParser",
    "register_parser",
    "get_parser",
    "SitemapCacheManager",
    "BASE_URL",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_HEADERS",
    "SITEMAP_URLS",
    "URLS",
]
