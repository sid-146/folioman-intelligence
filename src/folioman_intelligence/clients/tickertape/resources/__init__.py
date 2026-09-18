"""TickerTape resource modules."""

from folioman_intelligence.clients.tickertape.resources.base import _BaseResource
from folioman_intelligence.clients.tickertape.resources.mf import MutualFundsResource
from folioman_intelligence.clients.tickertape.resources.sitemap import SitemapResource

__all__ = [
    "_BaseResource",
    "MutualFundsResource",
    "SitemapResource",
]
