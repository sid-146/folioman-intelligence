"""Unit tests for SitemapCacheManager."""

import json
from pathlib import Path
import pytest

from folioman_intelligence.clients.tickertape.models import SitemapURL
from folioman_intelligence.clients.tickertape.storage import SitemapCacheManager


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "tickertape_cache"


def test_cache_save_and_load(temp_cache_dir: Path):
    manager = SitemapCacheManager(cache_dir=temp_cache_dir)
    assert not manager.exists("mf")

    items = [
        SitemapURL(record_id="M_AAA", url="https://www.tickertape.in/mutualfunds/fund-a-M_AAA", priority=0.8),
        SitemapURL(record_id="M_BBB", url="https://www.tickertape.in/mutualfunds/fund-b-M_BBB"),
    ]

    saved_path = manager.save("mf", items)
    assert saved_path.exists()
    assert manager.exists("mf")

    loaded_items = manager.load("mf")
    assert loaded_items is not None
    assert len(loaded_items) == 2
    assert loaded_items[0].record_id == "M_AAA"
    assert loaded_items[0].priority == 0.8
    assert loaded_items[1].record_id == "M_BBB"


def test_cache_load_nonexistent(temp_cache_dir: Path):
    manager = SitemapCacheManager(cache_dir=temp_cache_dir)
    assert manager.load("nonexistent") is None


def test_cache_load_corrupted(temp_cache_dir: Path):
    manager = SitemapCacheManager(cache_dir=temp_cache_dir)
    cache_file = manager.get_cache_path("corrupted")
    cache_file.write_text("{corrupted json", encoding="utf-8")

    assert manager.load("corrupted") is None


def test_cache_clear(temp_cache_dir: Path):
    manager = SitemapCacheManager(cache_dir=temp_cache_dir)
    items = [SitemapURL(record_id="M_1", url="https://example.com/1")]

    manager.save("mf", items)
    manager.save("stocks", items)

    assert manager.exists("mf")
    assert manager.exists("stocks")

    # Clear single category
    manager.clear("mf")
    assert not manager.exists("mf")
    assert manager.exists("stocks")

    # Clear all
    manager.clear()
    assert not manager.exists("stocks")
