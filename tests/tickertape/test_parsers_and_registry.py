"""Tests for parser registry and extension mechanics."""

import pytest
from folioman_intelligence.clients.tickertape.constants import URLS
from folioman_intelligence.clients.tickertape.errors import TickerTapeHTTPError
from folioman_intelligence.clients.tickertape.parsers import (
    BaseParser,
    MFParser,
    SitemapParser,
    get_parser,
    register_parser,
)
from folioman_intelligence.clients.tickertape.parsers.etf import ETFParser
from folioman_intelligence.clients.tickertape.parsers.screens import ScreenParser
from folioman_intelligence.clients.tickertape.parsers.stocks import StockParser


def test_parser_registry():
    mf_parser = get_parser("mf")
    assert isinstance(mf_parser, MFParser)

    sitemap_parser = get_parser("sitemap")
    assert isinstance(sitemap_parser, SitemapParser)

    stock_parser = get_parser("stocks")
    assert isinstance(stock_parser, StockParser)

    with pytest.raises(KeyError, match="No parser registered"):
        get_parser("non_existent_parser")


def test_register_custom_parser():
    class CustomParser(BaseParser[dict]):
        def parse(self, content):
            return {"parsed": True}

    register_parser("custom", CustomParser)
    parser = get_parser("custom")
    assert isinstance(parser, CustomParser)
    assert parser.parse("data") == {"parsed": True}


def test_stubs_raise_not_implemented():
    with pytest.raises(NotImplementedError):
        StockParser().parse("test")

    with pytest.raises(NotImplementedError):
        ETFParser().parse("test")

    with pytest.raises(NotImplementedError):
        ScreenParser().parse("test")


def test_error_str_representation():
    err_with_data = TickerTapeHTTPError(
        "Failed", status_code=500, response_data="Internal error details"
    )
    assert "[500] Failed - Internal error details" in str(err_with_data)

    err_no_data = TickerTapeHTTPError("Failed", status_code=404)
    assert "[404] Failed" in str(err_no_data)
