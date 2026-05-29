from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://culturegraph:culturegraph@localhost:5432/culturegraph"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, validation_alias=AliasChoices("PORT", "API_PORT"))
    upload_dir: str = "uploads"
    upload_max_bytes: int = 10 * 1024 * 1024
    cors_origins: str = "http://localhost:3000"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_timeout_seconds: float = 120.0
    anthropic_max_tokens: int = 2048
    jwt_secret: str | None = None
    jwt_expiration_days: int = 7
    google_client_id: str | None = None
    admin_emails: str = ""
    app_env: str = "development"

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"production", "prod"}

    @property
    def admin_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        }

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value


settings = Settings()
