"""Unit tests for AI rate limiter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.ai_rate_limiter import (
    _FIRM_KEY_PREFIX,
    _MATTER_KEY_PREFIX,
    _WINDOW_SECONDS,
    FIRM_LIMIT_PER_HOUR,
    MATTER_LIMIT_PER_HOUR,
    RateLimitExceededError,
    check_rate_limit,
    get_usage,
)


class TestRateLimitConstants:
    """Verify rate limit configuration."""

    def test_firm_limit_is_100(self):
        assert FIRM_LIMIT_PER_HOUR == 100

    def test_matter_limit_is_20(self):
        assert MATTER_LIMIT_PER_HOUR == 20

    def test_window_is_one_hour(self):
        assert _WINDOW_SECONDS == 3600

    def test_key_prefixes(self):
        assert _FIRM_KEY_PREFIX == "ai_rate:firm:"
        assert _MATTER_KEY_PREFIX == "ai_rate:matter:"


class TestRateLimitExceededError:
    """Test the RateLimitExceededError exception."""

    def test_exception_message(self):
        exc = RateLimitExceededError(scope="test_scope", limit=100)
        assert "test_scope" in str(exc)
        assert "100" in str(exc)

    def test_exception_attributes(self):
        exc = RateLimitExceededError(scope="firm:123", limit=100, window_seconds=3600)
        assert exc.scope == "firm:123"
        assert exc.limit == 100
        assert exc.window_seconds == 3600


class TestCheckRateLimit:
    """Test rate limit checking."""

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_allows_under_limit(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Atomic Lua script returns positive count when both limits pass
        mock_redis.eval.return_value = 6

        # Should not raise
        check_rate_limit(firm_id=uuid4(), matter_id=uuid4())

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_raises_when_firm_limit_exceeded(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Atomic script returns -1 when firm limit exceeded
        mock_redis.eval.return_value = -1

        with pytest.raises(RateLimitExceededError):
            check_rate_limit(firm_id=uuid4(), matter_id=uuid4())

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_raises_when_matter_limit_exceeded(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Atomic script returns -2 when matter limit exceeded
        mock_redis.eval.return_value = -2

        with pytest.raises(RateLimitExceededError):
            check_rate_limit(firm_id=uuid4(), matter_id=uuid4())

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_redis_failure_does_not_raise(self, mock_get_redis):
        """Redis failures should be swallowed — AI processing should continue."""
        mock_get_redis.side_effect = Exception("Redis connection failed")

        # Should NOT raise
        check_rate_limit(firm_id=uuid4(), matter_id=uuid4())


class TestGetUsage:
    """Test usage monitoring."""

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_returns_firm_usage(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        mock_redis.zcard.return_value = 42

        result = get_usage(firm_id=uuid4())
        assert "firm_calls_this_hour" in result
        assert result["firm_calls_this_hour"] == 42

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_returns_matter_usage(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis
        mock_redis.zcard.return_value = 7

        result = get_usage(matter_id=uuid4())
        assert "matter_calls_this_hour" in result
        assert result["matter_calls_this_hour"] == 7

    @patch("app.services.ai_rate_limiter._get_redis")
    def test_redis_failure_returns_empty(self, mock_get_redis):
        mock_get_redis.side_effect = Exception("Redis down")
        result = get_usage(firm_id=uuid4())
        assert result == {}
