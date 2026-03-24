"""Unit tests for branding service — config resolution, helpers."""

from __future__ import annotations

from app.services.branding_service import (
    DEFAULT_BRANDING,
    _hex_to_rgb,
    get_email_branding,
    get_pdf_branding,
)


class TestHexToRgb:
    def test_valid_hex(self):
        assert _hex_to_rgb("#1a2332") == (26, 35, 50)

    def test_hex_without_hash(self):
        assert _hex_to_rgb("c9a84c") == (201, 168, 76)

    def test_white(self):
        assert _hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_black(self):
        assert _hex_to_rgb("#000000") == (0, 0, 0)

    def test_invalid_hex_returns_default(self):
        assert _hex_to_rgb("xyz") == (26, 35, 50)

    def test_empty_returns_default(self):
        assert _hex_to_rgb("") == (26, 35, 50)

    def test_short_hex_returns_default(self):
        assert _hex_to_rgb("#fff") == (26, 35, 50)


class TestDefaultBranding:
    def test_has_required_keys(self):
        assert "primary_color" in DEFAULT_BRANDING
        assert "secondary_color" in DEFAULT_BRANDING
        assert "powered_by_visible" in DEFAULT_BRANDING
        assert DEFAULT_BRANDING["powered_by_visible"] is True

    def test_defaults_no_logo(self):
        assert DEFAULT_BRANDING["logo_url"] is None

    def test_default_colors(self):
        assert DEFAULT_BRANDING["primary_color"] == "#1a2332"
        assert DEFAULT_BRANDING["secondary_color"] == "#c9a84c"


class TestGetEmailBranding:
    def test_no_white_label(self):
        result = get_email_branding(None, "Test Firm")
        assert result["firm_name"] == "Test Firm"
        assert result["logo_url"] is None
        assert result["powered_by_visible"] is True

    def test_with_white_label(self):
        wl = {
            "firm_display_name": "Custom Firm",
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#ff0000",
            "powered_by_visible": False,
        }
        result = get_email_branding(wl, "Fallback Name")
        assert result["firm_name"] == "Custom Firm"
        assert result["logo_url"] == "https://example.com/logo.png"
        assert result["primary_color"] == "#ff0000"
        assert result["powered_by_visible"] is False

    def test_uses_firm_name_fallback(self):
        wl = {"logo_url": "https://example.com/logo.png"}
        result = get_email_branding(wl, "Smith & Associates")
        assert result["firm_name"] == "Smith & Associates"


class TestGetPdfBranding:
    def test_no_white_label(self):
        result = get_pdf_branding(None, "Test Firm")
        assert result["firm_name"] == "Test Firm"
        assert result["primary_color"] == (26, 35, 50)  # NAVY
        assert result["secondary_color"] == (201, 168, 76)  # GOLD

    def test_with_custom_colors(self):
        wl = {
            "primary_color": "#ff0000",
            "secondary_color": "#00ff00",
        }
        result = get_pdf_branding(wl, "Firm")
        assert result["primary_color"] == (255, 0, 0)
        assert result["secondary_color"] == (0, 255, 0)

    def test_partial_override(self):
        wl = {"primary_color": "#3366cc"}
        result = get_pdf_branding(wl, "Firm")
        assert result["primary_color"] == (51, 102, 204)
        assert result["secondary_color"] == (201, 168, 76)  # default GOLD


class TestWhiteLabelSchemas:
    def test_config_defaults(self):
        from app.schemas.firms import WhiteLabelConfig

        config = WhiteLabelConfig()
        assert config.logo_url is None
        assert config.primary_color is None
        assert config.powered_by_visible is True
        assert config.custom_domain_verified is False

    def test_update_partial(self):
        from app.schemas.firms import WhiteLabelUpdate

        update = WhiteLabelUpdate(primary_color="#ff0000")
        dumped = update.model_dump(exclude_unset=True)
        assert dumped == {"primary_color": "#ff0000"}
        assert "logo_url" not in dumped

    def test_config_full(self):
        from app.schemas.firms import WhiteLabelConfig

        config = WhiteLabelConfig(
            logo_url="https://example.com/logo.png",
            primary_color="#1a73e8",
            firm_display_name="Smith Law",
            custom_domain="estates.smithlaw.com",
            custom_domain_verified=True,
            powered_by_visible=False,
        )
        assert config.firm_display_name == "Smith Law"
        assert config.custom_domain_verified is True

    def test_logo_upload_response(self):
        from app.schemas.firms import LogoUploadResponse

        resp = LogoUploadResponse(
            upload_url="https://s3.../presigned",
            logo_url="https://api.../logo.png",
            field="logo_url",
        )
        assert resp.field == "logo_url"
