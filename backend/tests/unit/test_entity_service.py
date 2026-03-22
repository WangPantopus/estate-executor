"""Unit tests for entity service helpers — trust detection and pour-over logic."""

import pytest

from app.models.enums import EntityType, TransferMechanism


class TestTrustEntityTypes:
    """Verify trust entity type detection used for pour-over candidates."""

    def test_revocable_trust_is_trust(self):
        from app.services.entity_service import _TRUST_ENTITY_TYPES

        assert EntityType.revocable_trust in _TRUST_ENTITY_TYPES

    def test_irrevocable_trust_is_trust(self):
        from app.services.entity_service import _TRUST_ENTITY_TYPES

        assert EntityType.irrevocable_trust in _TRUST_ENTITY_TYPES

    def test_llc_is_not_trust(self):
        from app.services.entity_service import _TRUST_ENTITY_TYPES

        assert EntityType.llc not in _TRUST_ENTITY_TYPES

    def test_corporation_is_not_trust(self):
        from app.services.entity_service import _TRUST_ENTITY_TYPES

        assert EntityType.corporation not in _TRUST_ENTITY_TYPES

    def test_foundation_is_not_trust(self):
        from app.services.entity_service import _TRUST_ENTITY_TYPES

        assert EntityType.foundation not in _TRUST_ENTITY_TYPES


class TestEntityModel:
    """Verify the Entity model has the expected fields for the service layer."""

    def test_entity_has_matter_id(self):
        from app.models.entities import Entity

        assert hasattr(Entity, "matter_id")

    def test_entity_has_assets_relationship(self):
        from app.models.entities import Entity

        assert hasattr(Entity, "assets")

    def test_entity_has_entity_type(self):
        from app.models.entities import Entity

        assert hasattr(Entity, "entity_type")

    def test_entity_has_funding_status(self):
        from app.models.entities import Entity

        assert hasattr(Entity, "funding_status")

    def test_entity_has_metadata(self):
        from app.models.entities import Entity

        assert hasattr(Entity, "metadata_")


class TestEntitySchemas:
    """Verify entity schemas have expected fields."""

    def test_entity_create_has_asset_ids(self):
        from app.schemas.entities import EntityCreate

        fields = EntityCreate.model_fields
        assert "asset_ids" in fields

    def test_entity_update_has_asset_ids(self):
        from app.schemas.entities import EntityUpdate

        fields = EntityUpdate.model_fields
        assert "asset_ids" in fields

    def test_entity_map_response_has_pour_over(self):
        from app.schemas.entities import EntityMapResponse

        fields = EntityMapResponse.model_fields
        assert "pour_over_candidates" in fields

    def test_entity_map_response_has_unassigned(self):
        from app.schemas.entities import EntityMapResponse

        fields = EntityMapResponse.model_fields
        assert "unassigned_assets" in fields
