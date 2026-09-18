"""Parser for TickerTape XML sitemaps.

Parses standard sitemap.xml files (<urlset>) and sitemap indexes (<sitemapindex>)
into typed Pydantic models.
"""

from __future__ import annotations

import logging
from typing import Optional, Union
import xml.etree.ElementTree as ET

from folioman_intelligence.clients.tickertape.constants import SITEMAP_NAMESPACE
from folioman_intelligence.clients.tickertape.errors import TickerTapeParseError
from folioman_intelligence.clients.tickertape.models import SitemapReference, SitemapURL
from folioman_intelligence.clients.tickertape.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class SitemapParser(BaseParser[Union[list[SitemapURL], list[SitemapReference]]]):
    """Parser for XML sitemaps supporting both <urlset> and <sitemapindex>."""

    def __init__(self, content: bytes | str | None = None) -> None:
        self.content = content
        self.root: Optional[ET.Element] = None

    def parse(
        self,
        content: bytes | str | None = None,
    ) -> list[SitemapURL] | list[SitemapReference]:
        """Parse XML document and return list of SitemapURL or SitemapReference."""
        raw_content = content if content is not None else self.content
        if raw_content is None:
            raise TickerTapeParseError("No XML content provided to parse")

        try:
            self.root = ET.fromstring(raw_content)
        except ET.ParseError as exc:
            raise TickerTapeParseError(f"Malformed sitemap XML: {exc}") from exc

        root_tag = self._local_name(self.root.tag)

        if root_tag == "urlset":
            return self.parse_urlset()

        if root_tag == "sitemapindex":
            return self.parse_sitemap_index()

        raise TickerTapeParseError(f"Unsupported sitemap root element: {root_tag}")

    def parse_urlset(self) -> list[SitemapURL]:
        """Parse standard sitemap containing <url> elements."""
        if self.root is None:
            raise TickerTapeParseError(
                "parse() must be called first to initialize root"
            )

        results: list[SitemapURL] = []
        for element in self.root:
            if self._local_name(element.tag) != "url":
                continue
            sitemap_url = self.extract_url(element)
            if sitemap_url and self.validate(sitemap_url):
                results.append(sitemap_url)

        return results

    def parse_sitemap_index(self) -> list[SitemapReference]:
        """Parse a sitemap index containing references to child sitemaps."""
        if self.root is None:
            raise TickerTapeParseError(
                "parse() must be called first to initialize root"
            )

        results: list[SitemapReference] = []
        for element in self.root:
            if self._local_name(element.tag) != "sitemap":
                continue
            loc = self._find_text(element, "loc")
            if not loc:
                continue

            last_modified = self._find_text(element, "lastmod")
            reference = SitemapReference(
                url=loc,
                last_modified=last_modified,
            )
            if self.validate(reference):
                results.append(reference)

        return results

    def extract_url(self, element: ET.Element) -> Optional[SitemapURL]:
        """Extract a <url> element into a SitemapURL object."""
        url = self._find_text(element, "loc")
        if not url:
            return None

        clean_url = url.rstrip("/")
        # Extract record ID, typically after the last hyphen (e.g. 'quant-active-fund-M_ESAF' -> 'M_ESAF')
        if "-" in clean_url:
            record_id = clean_url.split("-")[-1]
        else:
            record_id = clean_url.split("/")[-1]

        last_modified = self._find_text(element, "lastmod")
        change_frequency = self._find_text(element, "changefreq")
        priority_text = self._find_text(element, "priority")

        priority: Optional[float] = None
        if priority_text:
            try:
                priority = float(priority_text)
            except ValueError:
                priority = None

        return SitemapURL(
            record_id=record_id,
            url=url,
            last_modified=last_modified,
            change_frequency=change_frequency,
            priority=priority,
        )

    def validate(self, item: SitemapURL | SitemapReference) -> bool:
        """Validate parsed sitemap item URL."""
        if not item.url:
            return False
        return item.url.startswith(("http://", "https://"))

    @staticmethod
    def _local_name(tag: str) -> str:
        """Extract local XML tag name, stripping namespace if present."""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    @classmethod
    def _find_text(cls, element: ET.Element, tag_name: str) -> Optional[str]:
        """Find child element by local tag name and return stripped text."""
        for child in element:
            if cls._local_name(child.tag) == tag_name:
                if child.text:
                    return child.text.strip()
        return None
