"""Unit tests for enterprise SSO service — config validation, helpers."""

from __future__ import annotations

import pytest

from app.services.sso_service import _validate_config


class TestValidateConfig:
    def test_saml_with_metadata_url(self):
        _validate_config("saml", {"saml_metadata_url": "https://idp.example.com/metadata"})

    def test_saml_with_metadata_xml(self):
        _validate_config("saml", {"saml_metadata_xml": "<xml>...</xml>"})

    def test_saml_missing_both(self):
        with pytest.raises(Exception, match="metadata_url or metadata_xml"):
            _validate_config("saml", {})

    def test_oidc_valid(self):
        _validate_config(
            "oidc",
            {
                "oidc_discovery_url": "https://idp.example.com/.well-known/openid-configuration",
                "oidc_client_id": "client-123",
            },
        )

    def test_oidc_missing_discovery(self):
        with pytest.raises(Exception, match="discovery URL"):
            _validate_config("oidc", {"oidc_client_id": "abc"})

    def test_oidc_missing_client_id(self):
        with pytest.raises(Exception, match="client ID"):
            _validate_config("oidc", {"oidc_discovery_url": "https://..."})

    def test_unknown_protocol(self):
        with pytest.raises(Exception, match="Unsupported protocol"):
            _validate_config("ldap", {})


class TestSSOSchemas:
    def test_config_create_saml(self):
        from app.schemas.sso import SSOConfigCreate

        config = SSOConfigCreate(
            protocol="saml",
            saml_metadata_url="https://idp.example.com/metadata",
            allowed_domains=["example.com"],
        )
        assert config.protocol == "saml"
        assert config.enforce_sso is False
        assert config.auto_provision is True
        assert config.default_role == "member"

    def test_config_create_oidc(self):
        from app.schemas.sso import SSOConfigCreate

        config = SSOConfigCreate(
            protocol="oidc",
            oidc_discovery_url="https://idp.example.com/.well-known/openid-configuration",
            oidc_client_id="client-123",
            enforce_sso=True,
        )
        assert config.protocol == "oidc"
        assert config.enforce_sso is True

    def test_config_update_partial(self):
        from app.schemas.sso import SSOConfigUpdate

        update = SSOConfigUpdate(enforce_sso=True)
        dumped = update.model_dump(exclude_unset=True)
        assert dumped == {"enforce_sso": True}

    def test_response_excludes_secret(self):
        from datetime import UTC, datetime
        from uuid import uuid4

        from app.schemas.sso import SSOConfigResponse

        resp = SSOConfigResponse(
            id=uuid4(),
            firm_id=uuid4(),
            protocol="oidc",
            oidc_discovery_url="https://example.com",
            oidc_client_id="client-123",
            enabled=True,
            enforce_sso=False,
            auto_provision=True,
            default_role="member",
            allowed_domains=["example.com"],
            verified=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        # oidc_client_secret should not be in the response model
        assert not hasattr(resp, "oidc_client_secret")

    def test_login_url_response(self):
        from app.schemas.sso import SSOLoginUrlResponse

        resp = SSOLoginUrlResponse(
            login_url="https://auth0.example.com/authorize?connection=sso-abc",
            connection_name="sso-abc",
            protocol="saml",
        )
        assert "connection=sso-abc" in resp.login_url
