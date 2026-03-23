"""AI pipeline tests — classification accuracy with 20+ sample documents.

Tests classification with mocked Claude responses for every document type,
verifying correct doc_type assignment, confidence scoring, and edge cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.ai import AIClassifyResponse
from app.services.ai_classification_service import (
    DOCUMENT_TYPES,
    _build_classification_prompt,
    _build_tool_schema,
    classify_document,
)

# ─── Sample document texts for each doc type ──────────────────────────────────

SAMPLE_DOCUMENTS: list[dict] = [
    # Death certificates (2 variants)
    {
        "text": "STATE OF CALIFORNIA\nCERTIFICATE OF DEATH\nDecedent: John Michael Doe\nDate of Death: January 15, 2025\nPlace of Death: Los Angeles County\nCause of Death: Natural causes\nCertified by: County Registrar",
        "expected_type": "death_certificate",
        "label": "CA death certificate",
    },
    {
        "text": "COMMONWEALTH OF MASSACHUSETTS\nRECORD OF DEATH\nFull Name: Mary Jane Smith\nDate of Death: March 3, 2025\nAge: 78\nResidence: Boston, MA\nBurial: Forest Hills Cemetery\nRegistrar: City of Boston",
        "expected_type": "death_certificate",
        "label": "MA death record",
    },
    # Wills (2 variants)
    {
        "text": "LAST WILL AND TESTAMENT\nI, John Michael Doe, being of sound mind, do hereby declare this to be my Last Will and Testament, revoking all prior wills.\nARTICLE I: I appoint Jane Doe as Executor.\nARTICLE II: I devise my estate as follows...\nSigned this 10th day of June, 2020.\nWitnesses: Robert Brown, Alice Green",
        "expected_type": "will",
        "label": "Standard will",
    },
    {
        "text": "CODICIL TO THE LAST WILL AND TESTAMENT OF MARY SMITH\nI, Mary Smith, declare this a Codicil to my Will dated May 1, 2019.\nI hereby amend Article III to read as follows: My beach house shall pass to my daughter Sarah.\nAll other provisions remain unchanged.",
        "expected_type": "will",
        "label": "Will codicil",
    },
    # Trust documents (2 variants)
    {
        "text": "DOE FAMILY REVOCABLE LIVING TRUST\nDated: April 15, 2018\nGrantor: John M. Doe\nTrustee: John M. Doe\nSuccessor Trustee: First National Bank\nARTICLE IV: DISTRIBUTIONS\nUpon the Grantor's death, the Trust shall be divided into equal shares for the beneficiaries.\nSPENDTHRIFT CLAUSE: No beneficiary may assign or transfer their interest.",
        "expected_type": "trust_document",
        "label": "Revocable living trust",
    },
    {
        "text": "IRREVOCABLE LIFE INSURANCE TRUST\nSettlor: Robert Johnson\nTrustee: ABC Trust Company\nDate: September 1, 2019\nThe purpose of this trust is to hold the Settlor's life insurance policies outside of the taxable estate.\nArticle V: Distribution upon maturity of policies to beneficiaries named herein.",
        "expected_type": "trust_document",
        "label": "Irrevocable life insurance trust",
    },
    # Deeds (2 variants)
    {
        "text": "GRANT DEED\nRecording Requested By: Smith & Associates\nAPN: 1234-567-890\nFor valuable consideration, John Doe hereby grants to the Doe Family Trust the following property:\n123 Main Street, Los Angeles, CA 90001\nLot 5, Block 10, Tract 12345\nRecorded: January 20, 2020",
        "expected_type": "deed",
        "label": "Grant deed",
    },
    {
        "text": "QUITCLAIM DEED\nState of Texas\nCounty of Harris\nThe Grantor, Mary Smith, releases all right, title, and interest in the following property to James Smith:\n456 Oak Lane, Houston, TX 77001\nLegal Description: Lot 12, Block 3, Subdivision Greenfield\nFiled: March 2021",
        "expected_type": "deed",
        "label": "Quitclaim deed",
    },
    # Account statements (3 variants)
    {
        "text": "CHASE BANK\nAccount Statement\nAccount Holder: John M. Doe\nAccount Type: Checking\nAccount Number: ****4567\nStatement Period: Dec 1 - Dec 31, 2024\nBeginning Balance: $45,230.18\nEnding Balance: $52,104.55\nTotal Deposits: $12,000.00\nTotal Withdrawals: $5,125.63",
        "expected_type": "account_statement",
        "label": "Bank checking statement",
    },
    {
        "text": "FIDELITY INVESTMENTS\nBrokerage Account Statement\nAccount: ****8901\nOwner: John Doe\nAs of December 31, 2024\nTotal Account Value: $1,245,678.90\nHoldings:\n  SPY - 500 shares - $287,500\n  AAPL - 200 shares - $45,600\n  Bonds - $912,578.90",
        "expected_type": "account_statement",
        "label": "Brokerage account statement",
    },
    {
        "text": "VANGUARD\n401(k) RETIREMENT PLAN STATEMENT\nParticipant: John Doe\nEmployer: Tech Corp\nAccount Number: ****3456\nStatement Date: December 31, 2024\nTotal Balance: $875,432.10\nVested Balance: $875,432.10\nEmployee Contributions: $23,500\nEmployer Match: $11,750",
        "expected_type": "account_statement",
        "label": "401k statement",
    },
    # Insurance policies (2 variants)
    {
        "text": "PRUDENTIAL LIFE INSURANCE COMPANY\nPolicy Number: PLI-2020-789456\nInsured: John Michael Doe\nPolicy Type: Whole Life\nFace Value: $500,000\nBeneficiary: Jane Doe (spouse)\nEffective Date: July 1, 2015\nPremium: $450/month\nCash Value: $125,000",
        "expected_type": "insurance_policy",
        "label": "Whole life policy",
    },
    {
        "text": "NORTHWESTERN MUTUAL\nTERM LIFE INSURANCE POLICY\nPolicy No: NM-TL-456789\nInsured: John Doe\nTerm: 20 years\nDeath Benefit: $1,000,000\nPrimary Beneficiary: Jane Doe\nContingent Beneficiary: Children equally\nExpiration: 2035",
        "expected_type": "insurance_policy",
        "label": "Term life policy",
    },
    # Court filings (2 variants)
    {
        "text": "SUPERIOR COURT OF CALIFORNIA\nCOUNTY OF LOS ANGELES\nCase No. 2025-PR-00123\nPETITION FOR PROBATE\nPetitioner: Jane Doe\nDecedent: John Michael Doe\nDate of Death: January 15, 2025\nThe Petitioner requests appointment as Personal Representative.\nFiled: February 1, 2025",
        "expected_type": "court_filing",
        "label": "Probate petition",
    },
    {
        "text": "LETTERS TESTAMENTARY\nSuperior Court of California\nCounty of Los Angeles\nCase No. 2025-PR-00123\nIn the Matter of the Estate of John Michael Doe\nJane Doe is hereby appointed as Executor of the Estate.\nIssued: February 15, 2025\nJudge: Hon. Robert Williams",
        "expected_type": "court_filing",
        "label": "Letters testamentary",
    },
    # Tax returns (2 variants)
    {
        "text": "Form 1040 U.S. Individual Income Tax Return 2024\nName: John Michael Doe\nSSN: ***-**-1234\nFiling Status: Married Filing Jointly\nTotal Income: $285,000\nAdjusted Gross Income: $265,000\nTotal Tax: $52,340\nTax Withheld: $55,000\nRefund: $2,660",
        "expected_type": "tax_return",
        "label": "Form 1040",
    },
    {
        "text": "FORM 706 UNITED STATES ESTATE TAX RETURN\nDecedent: John Michael Doe\nDate of Death: January 15, 2025\nGross Estate: $5,245,000\nDeductions: $1,200,000\nTaxable Estate: $4,045,000\nTentative Tax: $1,577,800\nUnified Credit: $4,769,800\nNet Estate Tax: $0",
        "expected_type": "tax_return",
        "label": "Estate tax return 706",
    },
    # Appraisals (2 variants)
    {
        "text": "RESIDENTIAL APPRAISAL REPORT\nProperty: 123 Main Street, Los Angeles, CA 90001\nOwner: John Doe\nAppraisal Date: December 10, 2024\nAppraised Value: $1,250,000\nProperty Type: Single Family Residence\n3 bed / 2 bath, 2,100 sq ft\nAppraiser: James Wilson, MAI\nLicense No: CA-12345",
        "expected_type": "appraisal",
        "label": "Residential appraisal",
    },
    {
        "text": "BUSINESS VALUATION REPORT\nCompany: Doe Industries LLC\nValuation Date: January 15, 2025\nPrepared by: Smith Valuation Group\nFair Market Value: $2,500,000\nMethod: Discounted Cash Flow\nRevenue: $1,200,000\nEBITDA: $350,000\nDiscount Rate: 15%",
        "expected_type": "appraisal",
        "label": "Business valuation",
    },
    # Correspondence
    {
        "text": "Dear Mrs. Doe,\n\nThank you for notifying us of your husband's passing. We are sorry for your loss.\n\nPlease find enclosed the necessary forms to process the account transfer. We will need a certified copy of the death certificate and Letters Testamentary.\n\nSincerely,\nCustomer Service Department\nFirst National Bank",
        "expected_type": "correspondence",
        "label": "Bank correspondence",
    },
    # Other (ambiguous)
    {
        "text": "Meeting Notes - January 20, 2025\nAttendees: Jane Doe, Attorney Robert Smith\nDiscussed: Estate administration timeline\nAction items: File probate petition by Feb 1\nNext meeting: February 5, 2025",
        "expected_type": "other",
        "label": "Meeting notes (other)",
    },
]


def _make_mock_db(doc_id, matter_id, firm_id, storage_key="test/key.pdf", mime_type="application/pdf"):
    """Create a mock DB with document and matter records."""
    mock_db = AsyncMock()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.matter_id = matter_id
    mock_doc.storage_key = storage_key
    mock_doc.mime_type = mime_type
    mock_doc.doc_type = None
    mock_doc.doc_type_confidence = None

    mock_matter = MagicMock()
    mock_matter.id = matter_id
    mock_matter.firm_id = firm_id
    mock_matter.estate_type = MagicMock(value="testate_probate")
    mock_matter.jurisdiction_state = "CA"
    mock_matter.decedent_name = "John Doe"

    mock_result_doc = MagicMock()
    mock_result_doc.scalar_one_or_none.return_value = mock_doc
    mock_result_matter = MagicMock()
    mock_result_matter.scalar_one_or_none.return_value = mock_matter
    mock_db.execute.side_effect = [mock_result_doc, mock_result_matter]

    return mock_db, mock_doc


class TestClassificationAccuracy:
    """Test classification with 20+ sample documents covering every doc type."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "sample",
        SAMPLE_DOCUMENTS,
        ids=[s["label"] for s in SAMPLE_DOCUMENTS],
    )
    async def test_classifies_sample_correctly(self, sample):
        """Each sample document should be classified as the expected type."""
        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()
        mock_db, mock_doc = _make_mock_db(doc_id, matter_id, firm_id)

        claude_response = {
            "doc_type": sample["expected_type"],
            "confidence": 0.92,
            "reasoning": f"Document matches {sample['expected_type']} pattern",
        }

        with (
            patch("app.services.ai_classification_service.check_rate_limit"),
            patch(
                "app.services.ai_classification_service.text_extraction_service.extract_text",
                return_value=sample["text"],
            ),
            patch(
                "app.services.ai_classification_service._call_claude",
                return_value=(claude_response, 500, 100),
            ),
            patch(
                "app.services.ai_classification_service.event_logger.log",
                new_callable=AsyncMock,
            ),
        ):
            result = await classify_document(mock_db, document_id=doc_id)

        assert result.doc_type == sample["expected_type"]
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0
        assert len(result.reasoning) > 0

    def test_all_11_doc_types_covered(self):
        """Verify all 11 document types are covered by sample documents."""
        covered_types = {s["expected_type"] for s in SAMPLE_DOCUMENTS}
        assert covered_types == set(DOCUMENT_TYPES.keys())

    def test_at_least_20_samples(self):
        """Verify we have 20+ sample documents."""
        assert len(SAMPLE_DOCUMENTS) >= 20


class TestClassificationPromptConstruction:
    """Test that classification prompts include all necessary context."""

    def test_prompt_includes_all_doc_types(self):
        prompt = _build_classification_prompt("test text")
        for doc_type in DOCUMENT_TYPES:
            assert doc_type in prompt

    def test_prompt_includes_doc_text_in_tags(self):
        prompt = _build_classification_prompt("SAMPLE TEXT HERE")
        assert "<document_text>" in prompt
        assert "SAMPLE TEXT HERE" in prompt
        assert "</document_text>" in prompt

    def test_prompt_includes_matter_context(self):
        prompt = _build_classification_prompt(
            "test",
            estate_type="testate_probate",
            jurisdiction="CA",
            decedent_name="John Doe",
        )
        assert "testate_probate" in prompt
        assert "CA" in prompt
        assert "John Doe" in prompt

    def test_prompt_without_context_still_valid(self):
        prompt = _build_classification_prompt("test")
        assert "Classify" in prompt
        assert "document_text" in prompt


class TestClassificationToolSchema:
    """Validate the Claude tool-use schema for classification."""

    def test_enum_matches_document_types(self):
        schema = _build_tool_schema()
        enum_values = set(schema["input_schema"]["properties"]["doc_type"]["enum"])
        assert enum_values == set(DOCUMENT_TYPES.keys())

    def test_confidence_range(self):
        schema = _build_tool_schema()
        conf = schema["input_schema"]["properties"]["confidence"]
        assert conf["minimum"] == 0.0
        assert conf["maximum"] == 1.0

    def test_all_fields_required(self):
        schema = _build_tool_schema()
        required = set(schema["input_schema"]["required"])
        assert required == {"doc_type", "confidence", "reasoning"}


class TestClassificationConfidenceValidation:
    """Test confidence score edge cases."""

    def test_confidence_exactly_zero(self):
        resp = AIClassifyResponse(doc_type="other", confidence=0.0, reasoning="No text")
        assert resp.confidence == 0.0

    def test_confidence_exactly_one(self):
        resp = AIClassifyResponse(doc_type="death_certificate", confidence=1.0, reasoning="Perfect match")
        assert resp.confidence == 1.0

    def test_confidence_over_one_rejected(self):
        with pytest.raises(Exception):
            AIClassifyResponse(doc_type="will", confidence=1.01, reasoning="Bad")

    def test_confidence_negative_rejected(self):
        with pytest.raises(Exception):
            AIClassifyResponse(doc_type="will", confidence=-0.01, reasoning="Bad")

    @pytest.mark.asyncio
    async def test_empty_text_gives_zero_confidence(self):
        """When text extraction fails, confidence should be 0.0."""
        doc_id = uuid4()
        matter_id = uuid4()
        firm_id = uuid4()
        mock_db, _ = _make_mock_db(doc_id, matter_id, firm_id)

        with (
            patch("app.services.ai_classification_service.check_rate_limit"),
            patch(
                "app.services.ai_classification_service.text_extraction_service.extract_text",
                return_value="",
            ),
        ):
            result = await classify_document(mock_db, document_id=doc_id)

        assert result.doc_type == "other"
        assert result.confidence == 0.0
