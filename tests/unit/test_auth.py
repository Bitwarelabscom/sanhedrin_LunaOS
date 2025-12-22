"""
Tests for authentication and security middleware.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from sanhedrin.auth.middleware import (
    APIKeyConfig,
    APIKeyValidator,
    RateLimitConfig,
    RateLimiter,
    SecurityConfig,
    generate_api_key,
)


class TestAPIKeyValidator:
    """Tests for API key validation."""

    def test_validate_valid_key(self) -> None:
        """Valid key is accepted."""
        config = APIKeyConfig(enabled=True, keys={"test-key-123"})
        validator = APIKeyValidator(config)

        assert validator.validate("test-key-123")

    def test_validate_invalid_key(self) -> None:
        """Invalid key is rejected."""
        config = APIKeyConfig(enabled=True, keys={"test-key-123"})
        validator = APIKeyValidator(config)

        assert not validator.validate("wrong-key")

    def test_validate_empty_key(self) -> None:
        """Empty key is rejected."""
        config = APIKeyConfig(enabled=True, keys={"test-key-123"})
        validator = APIKeyValidator(config)

        assert not validator.validate("")
        assert not validator.validate(None)

    def test_validate_multiple_keys(self) -> None:
        """Multiple keys can be validated."""
        config = APIKeyConfig(
            enabled=True,
            keys={"key-1", "key-2", "key-3"},
        )
        validator = APIKeyValidator(config)

        assert validator.validate("key-1")
        assert validator.validate("key-2")
        assert validator.validate("key-3")
        assert not validator.validate("key-4")

    def test_add_key(self) -> None:
        """Can add keys dynamically."""
        config = APIKeyConfig(enabled=True, keys=set())
        validator = APIKeyValidator(config)

        assert not validator.validate("new-key")

        validator.add_key("new-key")
        assert validator.validate("new-key")

    def test_remove_key(self) -> None:
        """Can remove keys dynamically."""
        config = APIKeyConfig(enabled=True, keys={"test-key"})
        validator = APIKeyValidator(config)

        assert validator.validate("test-key")

        validator.remove_key("test-key")
        assert not validator.validate("test-key")


class TestGenerateAPIKey:
    """Tests for API key generation."""

    def test_generate_api_key_format(self) -> None:
        """Generated key has correct format."""
        key = generate_api_key()

        assert key.startswith("sk_")
        assert len(key) > 10

    def test_generate_api_key_custom_prefix(self) -> None:
        """Generated key uses custom prefix."""
        key = generate_api_key(prefix="pk")

        assert key.startswith("pk_")

    def test_generate_api_key_unique(self) -> None:
        """Generated keys are unique."""
        keys = [generate_api_key() for _ in range(100)]

        assert len(set(keys)) == 100


class TestRateLimiter:
    """Tests for rate limiting."""

    def test_allows_initial_requests(self) -> None:
        """Initial requests are allowed."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            burst_size=5,
        )
        limiter = RateLimiter(config)

        allowed, info = limiter.is_allowed("client-1")

        assert allowed
        assert info["remaining_tokens"] >= 0

    def test_blocks_after_burst(self) -> None:
        """Blocks after burst limit exceeded."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            burst_size=3,
        )
        limiter = RateLimiter(config)

        # Use up burst
        for _ in range(3):
            allowed, _ = limiter.is_allowed("client-1")
            assert allowed

        # Next request should be blocked
        allowed, _ = limiter.is_allowed("client-1")
        assert not allowed

    def test_different_clients_independent(self) -> None:
        """Different clients have independent limits."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            burst_size=2,
        )
        limiter = RateLimiter(config)

        # Exhaust client-1
        limiter.is_allowed("client-1")
        limiter.is_allowed("client-1")
        allowed1, _ = limiter.is_allowed("client-1")

        # client-2 should still be allowed
        allowed2, _ = limiter.is_allowed("client-2")

        assert not allowed1
        assert allowed2

    def test_minute_limit(self) -> None:
        """Per-minute limit is enforced."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=3,
            burst_size=100,  # High burst to test minute limit
        )
        limiter = RateLimiter(config)

        # Make 3 requests
        for _ in range(3):
            allowed, _ = limiter.is_allowed("client-1")
            assert allowed

        # 4th should fail due to minute limit
        allowed, info = limiter.is_allowed("client-1")
        assert not allowed
        assert info["minute_remaining"] <= 0

    def test_returns_limit_info(self) -> None:
        """Returns rate limit info."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            burst_size=5,
        )
        limiter = RateLimiter(config)

        _, info = limiter.is_allowed("client-1")

        assert "remaining_tokens" in info
        assert "minute_remaining" in info
        assert "hour_remaining" in info


class TestSecurityConfig:
    """Tests for security configuration."""

    def test_default_config(self) -> None:
        """Default config has sensible values."""
        config = SecurityConfig()

        assert not config.api_key.enabled
        assert config.rate_limit.enabled
        assert "/" in config.public_paths
        assert "/health" in config.public_paths

    def test_public_paths(self) -> None:
        """Public paths are configurable."""
        config = SecurityConfig(
            public_paths={"/", "/custom"},
        )

        assert "/custom" in config.public_paths
