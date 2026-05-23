from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://culturegraph:culturegraph@localhost:5432/culturegraph"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, validation_alias=AliasChoices("PORT", "API_PORT"))
    upload_dir: str = "uploads"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
