import logging

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

    # Email
    resend_api_key: str = ""
    email_from: str = "notifications@estate-executor.com"

    # URLs
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Encryption
    encryption_master_key: str = ""

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def is_development(self) -> bool:
        return self.app_env == "development" or self.environment == "dev"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production" or self.environment == "production"

    @property
    def auth0_issuer(self) -> str:
        return f"https://{self.auth0_domain}/"

    @property
    def auth0_jwks_url(self) -> str:
        return f"https://{self.auth0_domain}/.well-known/jwks.json"

    def configure_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )


settings = Settings()
