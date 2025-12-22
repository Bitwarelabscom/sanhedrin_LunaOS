"""
Tests for caching utilities.
"""

import asyncio
import time

import pytest

from sanhedrin.utils.cache import (
    CacheEntry,
    LRUCache,
    cached,
    async_cached,
)


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_not_expired_without_ttl(self) -> None:
        """Entry without TTL never expires."""
        entry = CacheEntry(value="test")
        assert not entry.is_expired

    def test_not_expired_within_ttl(self) -> None:
        """Entry within TTL is not expired."""
        entry = CacheEntry(value="test", ttl=10.0)
        assert not entry.is_expired

    def test_expired_after_ttl(self) -> None:
        """Entry after TTL is expired."""
        entry = CacheEntry(value="test", ttl=0.01)
        time.sleep(0.02)
        assert entry.is_expired

    def test_touch_updates_accessed_at(self) -> None:
        """Touch updates accessed time."""
        entry = CacheEntry(value="test")
        original = entry.accessed_at
        time.sleep(0.01)
        entry.touch()
        assert entry.accessed_at > original


class TestLRUCache:
    """Tests for LRUCache."""

    def test_set_and_get(self) -> None:
        """Basic set and get."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing_key(self) -> None:
        """Get missing key returns None."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        assert cache.get("missing") is None

    def test_delete(self) -> None:
        """Delete removes entry."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        cache.set("key", "value")
        assert cache.delete("key")
        assert cache.get("key") is None

    def test_delete_missing(self) -> None:
        """Delete missing key returns False."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        assert not cache.delete("missing")

    def test_lru_eviction(self) -> None:
        """Least recently used is evicted when at capacity."""
        cache: LRUCache[str] = LRUCache(max_size=3)

        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")

        # Access "a" to make it recent
        cache.get("a")

        # Add new item, "b" should be evicted (oldest unused)
        cache.set("d", "4")

        assert cache.get("a") == "1"
        assert cache.get("b") is None  # Evicted
        assert cache.get("c") == "3"
        assert cache.get("d") == "4"

    def test_ttl_expiration(self) -> None:
        """Entries expire after TTL."""
        cache: LRUCache[str] = LRUCache(max_size=10, default_ttl=0.01)
        cache.set("key", "value")

        assert cache.get("key") == "value"
        time.sleep(0.02)
        assert cache.get("key") is None

    def test_per_entry_ttl(self) -> None:
        """Per-entry TTL overrides default."""
        cache: LRUCache[str] = LRUCache(max_size=10, default_ttl=10.0)
        cache.set("short", "value", ttl=0.01)
        cache.set("long", "value")

        time.sleep(0.02)
        assert cache.get("short") is None
        assert cache.get("long") == "value"

    def test_clear(self) -> None:
        """Clear removes all entries."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        cache.set("a", "1")
        cache.set("b", "2")
        cache.clear()
        assert len(cache) == 0

    def test_len(self) -> None:
        """Length returns entry count."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        assert len(cache) == 0
        cache.set("a", "1")
        assert len(cache) == 1

    def test_contains(self) -> None:
        """Contains check works."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        cache.set("a", "1")
        assert "a" in cache
        assert "b" not in cache

    def test_contains_expired(self) -> None:
        """Contains returns False for expired."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        cache.set("a", "1", ttl=0.01)
        time.sleep(0.02)
        assert "a" not in cache

    def test_cleanup_expired(self) -> None:
        """Cleanup removes expired entries."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        cache.set("a", "1", ttl=0.01)
        cache.set("b", "2", ttl=10.0)

        time.sleep(0.02)
        removed = cache.cleanup_expired()

        assert removed == 1
        assert "a" not in cache
        assert "b" in cache

    def test_hit_rate(self) -> None:
        """Hit rate is calculated correctly."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        cache.set("a", "1")

        cache.get("a")  # Hit
        cache.get("a")  # Hit
        cache.get("b")  # Miss

        assert cache.hit_rate == pytest.approx(2/3)

    def test_stats(self) -> None:
        """Stats returns correct info."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        cache.set("a", "1")
        cache.get("a")
        cache.get("b")

        stats = cache.stats
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestLRUCacheAsync:
    """Tests for async LRUCache operations."""

    @pytest.mark.asyncio
    async def test_async_set_and_get(self) -> None:
        """Async set and get."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        await cache.set_async("key", "value")
        assert await cache.get_async("key") == "value"

    @pytest.mark.asyncio
    async def test_async_delete(self) -> None:
        """Async delete."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        await cache.set_async("key", "value")
        assert await cache.delete_async("key")
        assert await cache.get_async("key") is None

    @pytest.mark.asyncio
    async def test_async_clear(self) -> None:
        """Async clear."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        await cache.set_async("a", "1")
        await cache.clear_async()
        assert len(cache) == 0

    @pytest.mark.asyncio
    async def test_async_cleanup(self) -> None:
        """Async cleanup."""
        cache: LRUCache[str] = LRUCache(max_size=10)
        await cache.set_async("a", "1", ttl=0.01)
        await asyncio.sleep(0.02)
        removed = await cache.cleanup_expired_async()
        assert removed == 1


class TestCachedDecorator:
    """Tests for @cached decorator."""

    def test_caches_result(self) -> None:
        """Function result is cached."""
        cache: LRUCache[int] = LRUCache(max_size=10)
        call_count = 0

        @cached(cache)
        def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(5) == 10
        assert call_count == 1  # Only called once

    def test_different_args_different_cache(self) -> None:
        """Different args use different cache entries."""
        cache: LRUCache[int] = LRUCache(max_size=10)

        @cached(cache)
        def expensive(x: int) -> int:
            return x * 2

        assert expensive(5) == 10
        assert expensive(6) == 12
        assert len(cache) == 2

    def test_custom_key_func(self) -> None:
        """Custom key function is used."""
        cache: LRUCache[int] = LRUCache(max_size=10)

        @cached(cache, key_func=lambda x: f"custom:{x}")
        def expensive(x: int) -> int:
            return x * 2

        expensive(5)
        assert "custom:5" in cache


class TestAsyncCachedDecorator:
    """Tests for @async_cached decorator."""

    @pytest.mark.asyncio
    async def test_caches_async_result(self) -> None:
        """Async function result is cached."""
        cache: LRUCache[int] = LRUCache(max_size=10)
        call_count = 0

        @async_cached(cache)
        async def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert await expensive(5) == 10
        assert await expensive(5) == 10
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_with_ttl(self) -> None:
        """Async caching with TTL works."""
        cache: LRUCache[int] = LRUCache(max_size=10)
        call_count = 0

        @async_cached(cache, ttl=0.01)
        async def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert await expensive(5) == 10
        await asyncio.sleep(0.02)
        assert await expensive(5) == 10
        assert call_count == 2  # Called twice due to expiry
