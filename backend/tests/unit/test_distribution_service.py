"""Unit tests for the distribution ledger — model, schemas, service helpers."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.enums import DistributionType


class TestDistributionTypeEnum:
    """Verify distribution type enum values."""

    def test_cash(self):
        assert DistributionType.cash == "cash"

    def test_asset_transfer(self):
        assert DistributionType.asset_transfer == "asset_transfer"

    def test_in_kind(self):
        assert DistributionType.in_kind == "in_kind"

    def test_all_values(self):
        values = {e.value for e in DistributionType}
        assert values == {"cash", "asset_transfer", "in_kind"}


class TestDistributionModel:
    """Verify the Distribution model has expected fields."""

    def test_has_matter_id(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "matter_id")

    def test_has_asset_id(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "asset_id")

    def test_has_beneficiary_stakeholder_id(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "beneficiary_stakeholder_id")

    def test_has_amount(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "amount")

    def test_has_description(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "description")

    def test_has_distribution_type(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "distribution_type")

    def test_has_distribution_date(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "distribution_date")

    def test_has_receipt_acknowledged(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "receipt_acknowledged")

    def test_has_receipt_acknowledged_at(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "receipt_acknowledged_at")

    def test_has_notes(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "notes")

    def test_has_beneficiary_relationship(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "beneficiary")

    def test_has_asset_relationship(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "asset")

    def test_has_matter_relationship(self):
        from app.models.distributions import Distribution
        assert hasattr(Distribution, "matter")

    def test_table_name(self):
        from app.models.distributions import Distribution
        assert Distribution.__tablename__ == "distributions"


class TestDistributionSchemas:
    """Verify distribution schema fields."""

    def test_distribution_create_fields(self):
        from app.schemas.distributions import DistributionCreate
        fields = DistributionCreate.model_fields
        assert "beneficiary_stakeholder_id" in fields
        assert "amount" in fields
        assert "description" in fields
        assert "distribution_type" in fields
        assert "distribution_date" in fields
        assert "asset_id" in fields
        assert "notes" in fields

    def test_distribution_response_fields(self):
        from app.schemas.distributions import DistributionResponse
        fields = DistributionResponse.model_fields
        assert "id" in fields
        assert "matter_id" in fields
        assert "beneficiary_name" in fields
        assert "asset_title" in fields
        assert "receipt_acknowledged" in fields
        assert "receipt_acknowledged_at" in fields

    def test_distribution_summary_response_fields(self):
        from app.schemas.distributions import DistributionSummaryResponse
        fields = DistributionSummaryResponse.model_fields
        assert "total_distributed" in fields
        assert "total_distributions" in fields
        assert "total_acknowledged" in fields
        assert "total_pending" in fields
        assert "by_beneficiary" in fields
        assert "by_type" in fields

    def test_beneficiary_summary_item_fields(self):
        from app.schemas.distributions import BeneficiarySummaryItem
        fields = BeneficiarySummaryItem.model_fields
        assert "stakeholder_id" in fields
        assert "beneficiary_name" in fields
        assert "total_distributed" in fields
        assert "distribution_count" in fields
        assert "acknowledged_count" in fields
        assert "pending_count" in fields


class TestDistributionSchemaValidation:
    """Test schema instantiation with valid data."""

    def test_create_distribution_create(self):
        from app.schemas.distributions import DistributionCreate
        dist = DistributionCreate(
            beneficiary_stakeholder_id=uuid.uuid4(),
            amount=Decimal("50000.00"),
            description="Cash distribution from estate account",
            distribution_type=DistributionType.cash,
            distribution_date=date(2026, 3, 15),
        )
        assert dist.amount == Decimal("50000.00")
        assert dist.distribution_type == DistributionType.cash

    def test_create_distribution_without_amount(self):
        from app.schemas.distributions import DistributionCreate
        dist = DistributionCreate(
            beneficiary_stakeholder_id=uuid.uuid4(),
            description="In-kind transfer of personal property",
            distribution_type=DistributionType.in_kind,
            distribution_date=date(2026, 4, 1),
        )
        assert dist.amount is None

    def test_create_distribution_with_asset(self):
        from app.schemas.distributions import DistributionCreate
        dist = DistributionCreate(
            beneficiary_stakeholder_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            amount=Decimal("250000.00"),
            description="Transfer of real estate property",
            distribution_type=DistributionType.asset_transfer,
            distribution_date=date(2026, 5, 1),
        )
        assert dist.asset_id is not None

    def test_create_distribution_response(self):
        from app.schemas.distributions import DistributionResponse
        resp = DistributionResponse(
            id=uuid.uuid4(),
            matter_id=uuid.uuid4(),
            asset_id=None,
            asset_title=None,
            beneficiary_stakeholder_id=uuid.uuid4(),
            beneficiary_name="Jane Doe",
            amount=Decimal("75000.00"),
            description="Quarterly distribution",
            distribution_type=DistributionType.cash,
            distribution_date=date(2026, 3, 1),
            receipt_acknowledged=True,
            receipt_acknowledged_at=datetime(2026, 3, 5, 10, 30),
            notes="Acknowledged by email",
            created_at=datetime(2026, 3, 1, 9, 0),
        )
        assert resp.beneficiary_name == "Jane Doe"
        assert resp.receipt_acknowledged is True

    def test_create_summary_response(self):
        from app.schemas.distributions import DistributionSummaryResponse, BeneficiarySummaryItem
        summary = DistributionSummaryResponse(
            total_distributed=Decimal("150000.00"),
            total_distributions=3,
            total_acknowledged=2,
            total_pending=1,
            by_beneficiary=[
                BeneficiarySummaryItem(
                    stakeholder_id=uuid.uuid4(),
                    beneficiary_name="Jane Doe",
                    total_distributed=Decimal("100000.00"),
                    distribution_count=2,
                    acknowledged_count=2,
                    pending_count=0,
                ),
                BeneficiarySummaryItem(
                    stakeholder_id=uuid.uuid4(),
                    beneficiary_name="John Doe",
                    total_distributed=Decimal("50000.00"),
                    distribution_count=1,
                    acknowledged_count=0,
                    pending_count=1,
                ),
            ],
            by_type={"cash": Decimal("100000.00"), "asset_transfer": Decimal("50000.00")},
        )
        assert summary.total_distributed == Decimal("150000.00")
        assert len(summary.by_beneficiary) == 2


class TestDistributionModelRegistered:
    """Verify Distribution is registered in models __init__."""

    def test_distribution_in_models(self):
        from app.models import Distribution
        assert Distribution is not None

    def test_distribution_type_in_enums(self):
        from app.models import DistributionType
        assert DistributionType is not None


class TestMatterHasDistributions:
    """Verify Matter model has distributions relationship."""

    def test_matter_has_distributions_attribute(self):
        from app.models.matters import Matter
        assert hasattr(Matter, "distributions")
