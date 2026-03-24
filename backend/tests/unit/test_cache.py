"""Unit tests for the Redis caching layer."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.cache import (
    _DASHBOARD_NS,
    _FIRM_SETTINGS_NS,
    _PERMISSIONS_NS,
    _TEMPLATES_NS,
    cache_delete,
    cache_get,
    cache_set,
    get_cached_dashboard,
    get_cached_firm_settings,
    get_cached_templates,
    get_cached_user_permissions,
    invalidate_dashboard,
    invalidate_firm_settings,
    invalidate_user_permissions,
    set_cached_dashboard,
    set_cached_firm_settings,
    set_cached_templates,
    set_cached_user_permissions,
)


class TestCacheGetSet:
    """Test generic cache_get and cache_set."""

    @patch("app.core.cache._get_redis")
    def test_cache_set_and_get(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # Test set
        cache_set("test", "key1", value={"foo": "bar"}, ttl_seconds=60)
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "cache:test:key1"
        assert call_args[0][1] == 60
        assert json.loads(call_args[0][2]) == {"foo": "bar"}

    @patch("app.core.cache._get_redis")
    def test_cache_get_hit(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"foo": "bar"})
        mock_get_redis.return_value = mock_redis

        result = cache_get("test", "key1")
        assert result == {"foo": "bar"}

    @patch("app.core.cache._get_redis")
    def test_cache_get_miss(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        result = cache_get("test", "key1")
        assert result is None

    @patch("app.core.cache._get_redis")
    def test_cache_get_redis_error_returns_none(self, mock_get_redis: MagicMock) -> None:
        mock_get_redis.side_effect = ConnectionError("Redis down")
        result = cache_get("test", "key1")
        assert result is None

    @patch("app.core.cache._get_redis")
    def test_cache_set_redis_error_does_not_raise(self, mock_get_redis: MagicMock) -> None:
        mock_get_redis.side_effect = ConnectionError("Redis down")
        # Should not raise
        cache_set("test", "key1", value="hello", ttl_seconds=60)

    @patch("app.core.cache._get_redis")
    def test_cache_delete(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        cache_delete("test", "key1")
        mock_redis.delete.assert_called_once_with("cache:test:key1")


class TestFirmSettingsCache:
    """Test firm settings caching helpers."""

    @patch("app.core.cache._get_redis")
    def test_set_and_get_firm_settings(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        settings_data = {"white_label": True, "timezone": "US/Eastern"}
        set_cached_firm_settings("firm-123", settings_data)

        mock_redis.setex.assert_called_once()
        key = mock_redis.setex.call_args[0][0]
        assert "firm_settings" in key
        assert "firm-123" in key

    @patch("app.core.cache._get_redis")
    def test_invalidate_firm_settings(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        invalidate_firm_settings("firm-123")
        mock_redis.delete.assert_called_once()


class TestPermissionsCache:
    """Test user permissions caching helpers."""

    @patch("app.core.cache._get_redis")
    def test_set_and_get_permissions(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        perms = {"role": "matter_admin", "permissions": ["task:read", "task:write"]}
        set_cached_user_permissions("user-1", "matter-1", perms)

        mock_redis.setex.assert_called_once()
        key = mock_redis.setex.call_args[0][0]
        assert "permissions" in key
        assert "user-1" in key
        assert "matter-1" in key

    @patch("app.core.cache._get_redis")
    def test_invalidate_matter_permissions(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_redis.scan.return_value = (0, ["cache:permissions:user-1:matter-1"])
        mock_get_redis.return_value = mock_redis

        invalidate_user_permissions("matter-1")
        mock_redis.scan.assert_called()


class TestTemplatesCache:
    """Test task template registry caching helpers."""

    @patch("app.core.cache._get_redis")
    def test_set_and_get_templates(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        templates = [{"key": "obtain_death_certs", "title": "Obtain Death Certificates"}]
        set_cached_templates("testate_probate", "CA", "_none_", templates)

        mock_redis.setex.assert_called_once()
        key = mock_redis.setex.call_args[0][0]
        assert "templates" in key
        assert "testate_probate" in key
        assert "CA" in key

    @patch("app.core.cache._get_redis")
    def test_get_templates_miss(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        result = get_cached_templates("testate_probate", "CA", "_none_")
        assert result is None


class TestDashboardCache:
    """Test dashboard caching helpers."""

    @patch("app.core.cache._get_redis")
    def test_set_and_get_dashboard(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        data = {"task_summary": {"total": 10}, "stakeholder_count": 3}
        set_cached_dashboard("matter-1", "matter_admin", data)

        mock_redis.setex.assert_called_once()
        key = mock_redis.setex.call_args[0][0]
        assert "dashboard" in key

    @patch("app.core.cache._get_redis")
    def test_invalidate_dashboard(self, mock_get_redis: MagicMock) -> None:
        mock_redis = MagicMock()
        mock_redis.scan.return_value = (0, ["cache:dashboard:matter-1:matter_admin"])
        mock_get_redis.return_value = mock_redis

        invalidate_dashboard("matter-1")
        mock_redis.scan.assert_called()
