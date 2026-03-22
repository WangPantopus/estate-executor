"""Unit tests for asset service helpers — status lifecycle and valuation mapping."""

import pytest

from app.models.enums import AssetStatus


class TestStatusLifecycle:
    """Test the ordered status lifecycle enforcement."""

    def _validate(self, current: AssetStatus, target: AssetStatus):
        """Import lazily to avoid cryptography import chain."""
        from app.services.asset_service import _validate_status_transition

        _validate_status_transition(current, target)

    def test_discovered_to_valued(self):
        self._validate(AssetStatus.discovered, AssetStatus.valued)

    def test_valued_to_transferred(self):
        self._validate(AssetStatus.valued, AssetStatus.transferred)

    def test_transferred_to_distributed(self):
        self._validate(AssetStatus.transferred, AssetStatus.distributed)

    def test_discovered_to_transferred_skipping_valued(self):
        self._validate(AssetStatus.discovered, AssetStatus.transferred)

    def test_discovered_to_distributed_skipping_all(self):
        self._validate(AssetStatus.discovered, AssetStatus.distributed)

    def test_backward_valued_to_discovered_raises(self):
        from app.core.exceptions import ConflictError

        with pytest.raises(ConflictError):
            self._validate(AssetStatus.valued, AssetStatus.discovered)

    def test_backward_distributed_to_discovered_raises(self):
        from app.core.exceptions import ConflictError

        with pytest.raises(ConflictError):
            self._validate(AssetStatus.distributed, AssetStatus.discovered)

    def test_same_status_raises(self):
        from app.core.exceptions import ConflictError

        with pytest.raises(ConflictError):
            self._validate(AssetStatus.valued, AssetStatus.valued)

    def test_backward_distributed_to_valued_raises(self):
        from app.core.exceptions import ConflictError

        with pytest.raises(ConflictError):
            self._validate(AssetStatus.distributed, AssetStatus.valued)

    def test_all_statuses_indexed(self):
        from app.services.asset_service import _STATUS_INDEX

        for status in AssetStatus:
            assert status in _STATUS_INDEX, f"{status} not in _STATUS_INDEX"


class TestValuationFieldMap:
    """Test the valuation type → field name mapping."""

    def test_date_of_death_maps_correctly(self):
        from app.services.asset_service import _VALUATION_FIELD_MAP

        assert _VALUATION_FIELD_MAP["date_of_death"] == "date_of_death_value"

    def test_current_estimate_maps_correctly(self):
        from app.services.asset_service import _VALUATION_FIELD_MAP

        assert _VALUATION_FIELD_MAP["current_estimate"] == "current_estimated_value"

    def test_final_appraised_maps_correctly(self):
        from app.services.asset_service import _VALUATION_FIELD_MAP

        assert _VALUATION_FIELD_MAP["final_appraised"] == "final_appraised_value"

    def test_all_types_have_matching_asset_fields(self):
        """Verify all valuation fields exist on the Asset model."""
        from app.models.assets import Asset
        from app.services.asset_service import _VALUATION_FIELD_MAP

        for val_type, field_name in _VALUATION_FIELD_MAP.items():
            assert hasattr(Asset, field_name), (
                f"Valuation type '{val_type}' maps to '{field_name}' "
                f"which doesn't exist on Asset model"
            )
