from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-to-a-random-secret"
    environment: str = "dev"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/estate_executor"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/estate_executor"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000"]
    cors_origins: list[str] = ["http://localhost:3000"]

    # Auth0
    auth0_domain: str = ""
    auth0_api_audience: str = ""
    auth0_algorithms: list[str] = ["RS256"]
    auth0_client_id: str = ""
    auth0_client_secret: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # AWS S3 / MinIO
    aws_s3_bucket: str = "estate-executor-documents"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_endpoint_url: str = ""  # Set to "http://localhost:9000" for MinIO

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Clio Integration
    clio_client_id: str = ""
    clio_client_secret: str = ""
    clio_redirect_uri: str = ""  # e.g. http://localhost:8000/api/v1/integrations/clio/callback
    clio_webhook_secret: str = ""
    clio_api_base_url: str = "https://app.clio.com"
    clio_auth_url: str = "https://app.clio.com/oauth/authorize"
    clio_token_url: str = "https://app.clio.com/oauth/token"

    # QuickBooks Online Integration
    qbo_client_id: str = ""
    qbo_client_secret: str = ""
    qbo_redirect_uri: str = ""
    qbo_webhook_verifier: str = ""
    qbo_environment: str = "sandbox"  # "sandbox" or "production"
    qbo_auth_url: str = "https://appcenter.intuit.com/connect/oauth2"
    qbo_token_url: str = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

    # DocuSign Integration
    docusign_integration_key: str = ""  # OAuth client ID
    docusign_secret_key: str = ""
    docusign_redirect_uri: str = ""
    docusign_webhook_secret: str = ""  # HMAC key for Connect
    docusign_base_url: str = "https://account-d.docusign.com"  # demo; prod: account.docusign.com
    docusign_auth_url: str = "https://account-d.docusign.com/oauth/auth"
    docusign_token_url: str = "https://account-d.docusign.com/oauth/token"
    docusign_api_base_url: str = "https://demo.docusign.net/restapi"  # prod: na*.docusign.net

    # Email
    resend_api_key: str = ""
    email_from: str = "Estate Executor <notifications@estate-executor.com>"
    mailpit_smtp_host: str = "localhost"
    mailpit_smtp_port: int = 1025

    # URLs
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Encryption
    encryption_master_key: str = ""

    # E2E testing
    e2e_mock_auth: bool = False

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Rate limiting (overridable per environment)
    rate_limit_enabled: bool = True
    rate_limit_strict: int = 10
    rate_limit_write: int = 30
    rate_limit_standard: int = 60
    rate_limit_relaxed: int = 120

    # CSRF
    csrf_enabled: bool = True

    # Monitoring & Observability
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1  # 10% of requests sampled for perf
    sentry_profiles_sample_rate: float = 0.1
    sentry_environment: str = ""  # defaults to app_env if empty
    uptimerobot_readonly_api_key: str = ""
    metrics_retention_hours: int = 24  # In-memory metrics window
    alert_error_rate_threshold: float = 0.05  # 5% error rate triggers alert
    alert_p99_latency_ms: float = 5000.0  # 5s p99 triggers alert
    alert_queue_depth_threshold: int = 100  # Celery queue depth alert
    alert_deadline_failure_window_hours: int = 24

    model_config = {"env_file": ".env", "extra": "ignore"}

    def model_post_init(self, __context: object) -> None:
        """Auto-disable rate limiting and CSRF in test environment unless explicitly set."""
        if self.app_env == "test":
            # Only override if the env var was NOT explicitly set (i.e. still at default)
            import os

            if "RATE_LIMIT_ENABLED" not in os.environ:
                object.__setattr__(self, "rate_limit_enabled", False)
            if "CSRF_ENABLED" not in os.environ:
                object.__setattr__(self, "csrf_enabled", False)

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development" or self.environment == "dev"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production" or self.environment == "production"

    def validate_production_secrets(self) -> list[str]:
        """Check that default/placeholder secrets are not used in production.

        Returns a list of warnings for any insecure defaults detected.
        """
        warnings: list[str] = []
        if not self.is_production:
            return warnings

        if self.app_secret_key == "change-me-to-a-random-secret":
            warnings.append("APP_SECRET_KEY is using the default placeholder value")
        if not self.encryption_master_key:
            warnings.append("ENCRYPTION_MASTER_KEY is not set")
        if not self.auth0_domain:
            warnings.append("AUTH0_DOMAIN is not configured")
        if not self.auth0_client_secret:
            warnings.append("AUTH0_CLIENT_SECRET is not configured")
        if self.e2e_mock_auth:
            warnings.append("E2E_MOCK_AUTH must be disabled in production")
        if any(
            origin in ("*", "http://localhost:3000")
            for origin in self.backend_cors_origins + self.cors_origins
        ):
            warnings.append("CORS origins contain localhost or wildcard — restrict for production")

        return warnings

    @property
    def auth0_issuer(self) -> str:
        return f"https://{self.auth0_domain}/"

    @property
    def auth0_jwks_url(self) -> str:
        return f"https://{self.auth0_domain}/.well-known/jwks.json"

    def configure_logging(self) -> None:
        from app.core.logging import configure_logging

        configure_logging(level=self.log_level, environment=self.app_env)


settings = Settings()
