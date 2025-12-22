"""
Caching utilities for Sanhedrin.

Provides in-memory caching with TTL support and LRU eviction.
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, Callable, Awaitable
from functools import wraps

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Entry in the cache with metadata."""

    value: T
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    ttl: float | None = None

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        """Update last accessed time."""
        self.accessed_at = time.time()


class LRUCache(Generic[T]):
    """
    Thread-safe LRU cache with TTL support.

    Features:
    - Least Recently Used eviction
    - Time-to-live for entries
    - Max size limit
    - Async-safe operations

    Example:
        >>> cache = LRUCache[str](max_size=100, default_ttl=300)
        >>> cache.set("key", "value")
        >>> cache.get("key")
        'value'
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float | None = None,
    ) -> None:
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds (None = no expiry)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = asyncio.Lock()

        # Stats
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> T | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        entry.touch()
        self._hits += 1

        return entry.value

    async def get_async(self, key: str) -> T | None:
        """Thread-safe async get."""
        async with self._lock:
            return self.get(key)

    def set(
        self,
        key: str,
        value: T,
        ttl: float | None = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
        """
        # Use default TTL if not specified
        entry_ttl = ttl if ttl is not None else self.default_ttl

        # Remove if exists to update order
        if key in self._cache:
            del self._cache[key]

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(value=value, ttl=entry_ttl)

    async def set_async(
        self,
        key: str,
        value: T,
        ttl: float | None = None,
    ) -> None:
        """Thread-safe async set."""
        async with self._lock:
            self.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def delete_async(self, key: str) -> bool:
        """Thread-safe async delete."""
        async with self._lock:
            return self.delete(key)

    def clear(self) -> None:
        """Clear all entries from cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    async def clear_async(self) -> None:
        """Thread-safe async clear."""
        async with self._lock:
            self.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    async def cleanup_expired_async(self) -> int:
        """Thread-safe async cleanup."""
        async with self._lock:
            return self.cleanup_expired()

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        entry = self._cache.get(key)
        if entry is None:
            return False
        if entry.is_expired:
            del self._cache[key]
            return False
        return True

    @property
    def hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


def cached(
    cache: LRUCache[T],
    key_func: Callable[..., str] | None = None,
    ttl: float | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to cache function results.

    Args:
        cache: Cache instance to use
        key_func: Function to generate cache key from args
        ttl: Optional TTL override

    Example:
        >>> cache = LRUCache[str](max_size=100)
        >>> @cached(cache)
        ... def expensive_function(x: int) -> str:
        ...     return str(x * 2)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"

            # Check cache
            result = cache.get(key)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return wrapper
    return decorator


def async_cached(
    cache: LRUCache[T],
    key_func: Callable[..., str] | None = None,
    ttl: float | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator to cache async function results.

    Args:
        cache: Cache instance to use
        key_func: Function to generate cache key from args
        ttl: Optional TTL override

    Example:
        >>> cache = LRUCache[str](max_size=100)
        >>> @async_cached(cache)
        ... async def expensive_async_function(x: int) -> str:
        ...     return str(x * 2)
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"

            # Check cache
            result = await cache.get_async(key)
            if result is not None:
                return result

            # Compute and cache
            result = await func(*args, **kwargs)
            await cache.set_async(key, result, ttl)
            return result

        return wrapper
    return decorator
