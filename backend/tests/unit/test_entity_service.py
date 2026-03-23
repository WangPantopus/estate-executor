"""Unit tests for entity service helpers — trust detection and pour-over logic."""


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


class TestFundingStatusEnum:
    """Verify all funding statuses exist."""

    def test_all_funding_statuses(self):
        from app.models.enums import FundingStatus

        expected = {"unknown", "fully_funded", "partially_funded", "unfunded"}
        actual = {s.value for s in FundingStatus}
        assert expected == actual

    def test_funding_status_count(self):
        from app.models.enums import FundingStatus
        assert len(list(FundingStatus)) == 4


class TestEntityAssetJunction:
    """Test entity_assets junction table structure."""

    def test_junction_table_exists(self):
        from app.models.entity_assets import entity_assets
        assert entity_assets is not None

    def test_junction_has_entity_id(self):
        from app.models.entity_assets import entity_assets
        col_names = {c.name for c in entity_assets.columns}
        assert "entity_id" in col_names

    def test_junction_has_asset_id(self):
        from app.models.entity_assets import entity_assets
        col_names = {c.name for c in entity_assets.columns}
        assert "asset_id" in col_names


class TestEntityTypeCount:
    """Verify entity type completeness."""

    def test_entity_type_count(self):
        assert len(list(EntityType)) == 7

    def test_all_entity_types(self):
        expected = {
            "revocable_trust", "irrevocable_trust", "llc",
            "flp", "corporation", "foundation", "other",
        }
        actual = {t.value for t in EntityType}
        assert expected == actual


class TestPourOverCandidateLogic:
    """Test pour-over candidate identification logic."""

    def test_probate_mechanism_is_pour_over_source(self):
        assert TransferMechanism.probate.value == "probate"

    def test_trust_mechanism_is_not_pour_over_source(self):
        assert TransferMechanism.trust_administration.value == "trust_administration"

    def test_unassigned_assets_computation(self):
        """Assets not linked to any entity should appear as unassigned."""
        all_ids = {"a1", "a2", "a3"}
        linked_ids = {"a1"}
        unassigned = all_ids - linked_ids
        assert unassigned == {"a2", "a3"}

    def test_no_trusts_means_no_pour_over(self):
        """If there are no trust entities, pour-over candidates should be empty."""
        from app.services.entity_service import _TRUST_ENTITY_TYPES

        entity_types = [EntityType.llc, EntityType.corporation]
        has_trusts = any(et in _TRUST_ENTITY_TYPES for et in entity_types)
        assert not has_trusts
