from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-to-a-random-secret"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/estate_executor"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/estate_executor"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000"]

    # Auth0
    auth0_domain: str = ""
    auth0_api_audience: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # AWS S3
    aws_s3_bucket: str = "estate-executor-documents"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

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
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
