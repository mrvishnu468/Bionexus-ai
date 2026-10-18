import time

import pytest

from app.core.cache_manager import CacheCapacityError, CacheError, DiskCache


def test_put_get_and_miss(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=20)
    assert cache.get("missing") is None
    cache.put("sample", b"expression")
    assert cache.get("sample") == b"expression"
    assert cache.stats()["used_bytes"] == 10


def test_lru_eviction_obeys_capacity(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=6)
    cache.put("older", b"1234")
    time.sleep(0.02)
    cache.put("newer", b"56")
    cache.put("third", b"abc")
    assert cache.get("older") is None
    assert cache.get("third") == b"abc"
    assert cache.stats()["used_bytes"] <= 6


def test_oversized_entry_is_rejected(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=3)
    with pytest.raises(CacheCapacityError):
        cache.put("large", b"four")


def test_active_entry_is_protected(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=5)
    cache.put("active", b"1234")
    with cache.lease("active"):
        with pytest.raises(CacheCapacityError):
            cache.put("another", b"xyz")
        assert cache.get("active") == b"1234"


def test_corrupt_data_is_rejected_and_removed(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=20)
    cache.put("corrupt", b"original")
    data_path, _ = cache._paths("corrupt")
    data_path.write_bytes(b"modified")
    assert cache.get("corrupt") is None
    assert cache.stats()["entry_count"] == 0


def test_cleanup_removes_expired_entries(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=20)
    cache.put("old", b"123")
    time.sleep(0.02)
    assert cache.cleanup(max_age_seconds=0) == 3
    assert cache.get("old") is None


def test_invalid_inputs_are_rejected(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=20)
    with pytest.raises(ValueError):
        cache.get("")
    with pytest.raises(TypeError):
        cache.put("wrong-type", "text")


def test_failed_replacement_preserves_existing_entry(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=5)
    cache.put("keep", b"12345")
    with pytest.raises(CacheCapacityError):
        cache.put("keep", b"123456")
    assert cache.get("keep") == b"12345"


def test_active_entry_cannot_be_replaced(tmp_path):
    cache = DiskCache(tmp_path, max_bytes=20)
    cache.put("protected", b"before")
    with cache.lease("protected"):
        with pytest.raises(CacheError):
            cache.put("protected", b"after")
    assert cache.get("protected") == b"before"
