"""Unit tests for text extraction service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.text_extraction_service import (
    _DOCX_TYPES,
    _IMAGE_TYPES,
    _MAX_CHARS,
    _PDF_TYPES,
    _truncate_text,
    extract_text,
)


class TestMimeTypeConstants:
    """Verify MIME type groupings are defined correctly."""

    def test_pdf_types_includes_application_pdf(self):
        assert "application/pdf" in _PDF_TYPES

    def test_image_types_includes_common_formats(self):
        assert "image/png" in _IMAGE_TYPES
        assert "image/jpeg" in _IMAGE_TYPES
        assert "image/tiff" in _IMAGE_TYPES

    def test_docx_types_includes_openxml(self):
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in _DOCX_TYPES
        )


class TestTruncateText:
    """Verify text truncation logic."""

    def test_short_text_unchanged(self):
        text = "Short text"
        result = _truncate_text(text)
        assert result == text

    def test_text_at_limit_unchanged(self):
        text = "a" * _MAX_CHARS
        result = _truncate_text(text)
        assert result == text

    def test_long_text_truncated(self):
        text = "word " * (_MAX_CHARS // 2)  # Way over limit
        result = _truncate_text(text)
        assert len(result) <= _MAX_CHARS + 100  # Allow for truncation suffix
        assert result.endswith("[... text truncated for processing ...]")

    def test_truncation_at_word_boundary(self):
        # Create text just over limit with spaces
        text = ("hello " * (_MAX_CHARS // 6 + 100))
        result = _truncate_text(text)
        # Should not end mid-word (before the truncation suffix)
        main_text = result.replace("\n[... text truncated for processing ...]", "")
        assert not main_text.endswith("hel")  # Shouldn't cut mid-word


class TestExtractText:
    """Test the main extract_text function."""

    @patch("app.services.text_extraction_service._download_file")
    @patch("app.services.text_extraction_service._extract_pdf")
    def test_pdf_extraction_called_for_pdf_mime(self, mock_pdf, mock_download):
        mock_download.return_value = b"fake pdf bytes"
        mock_pdf.return_value = "Extracted PDF text"

        result = extract_text("some/key.pdf", "application/pdf")

        mock_download.assert_called_once_with("some/key.pdf")
        mock_pdf.assert_called_once_with(b"fake pdf bytes")
        assert result == "Extracted PDF text"

    @patch("app.services.text_extraction_service._download_file")
    @patch("app.services.text_extraction_service._extract_image")
    def test_image_extraction_called_for_image_mime(self, mock_image, mock_download):
        mock_download.return_value = b"fake image bytes"
        mock_image.return_value = "OCR text from image"

        result = extract_text("some/key.png", "image/png")

        mock_download.assert_called_once()
        mock_image.assert_called_once_with(b"fake image bytes")
        assert result == "OCR text from image"

    @patch("app.services.text_extraction_service._download_file")
    @patch("app.services.text_extraction_service._extract_docx")
    def test_docx_extraction_called_for_docx_mime(self, mock_docx, mock_download):
        mock_download.return_value = b"fake docx bytes"
        mock_docx.return_value = "DOCX paragraph text"

        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        result = extract_text("some/key.docx", mime)

        mock_download.assert_called_once()
        mock_docx.assert_called_once_with(b"fake docx bytes")
        assert result == "DOCX paragraph text"

    @patch("app.services.text_extraction_service._download_file")
    def test_unsupported_mime_type_returns_empty(self, mock_download):
        mock_download.return_value = b"some bytes"
        result = extract_text("key", "application/octet-stream")
        assert result == ""

    @patch("app.services.text_extraction_service._download_file")
    def test_download_failure_returns_empty(self, mock_download):
        mock_download.side_effect = Exception("S3 error")
        result = extract_text("bad/key", "application/pdf")
        assert result == ""

    @patch("app.services.text_extraction_service._download_file")
    @patch("app.services.text_extraction_service._extract_pdf")
    def test_extraction_failure_returns_empty(self, mock_pdf, mock_download):
        mock_download.return_value = b"corrupt pdf"
        mock_pdf.side_effect = Exception("PDF parse error")

        result = extract_text("key.pdf", "application/pdf")
        assert result == ""

    @patch("app.services.text_extraction_service._download_file")
    @patch("app.services.text_extraction_service._extract_pdf")
    def test_empty_extraction_returns_empty(self, mock_pdf, mock_download):
        mock_download.return_value = b"empty pdf"
        mock_pdf.return_value = "   "  # Whitespace only

        result = extract_text("key.pdf", "application/pdf")
        assert result == ""

    @patch("app.services.text_extraction_service._download_file")
    @patch("app.services.text_extraction_service._extract_pdf")
    def test_long_text_is_truncated(self, mock_pdf, mock_download):
        mock_download.return_value = b"big pdf"
        mock_pdf.return_value = "word " * 100000  # Very long text

        result = extract_text("key.pdf", "application/pdf")
        assert len(result) < _MAX_CHARS + 200
        assert "[... text truncated" in result


class TestTokenLimit:
    """Verify token limit constants."""

    def test_max_tokens_is_5000(self):
        from app.services.text_extraction_service import _MAX_TOKENS

        assert _MAX_TOKENS == 5000

    def test_max_chars_is_4x_tokens(self):
        from app.services.text_extraction_service import _MAX_CHARS, _MAX_TOKENS

        assert _MAX_CHARS == _MAX_TOKENS * 4
