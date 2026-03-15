from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    google_client_id: str = Field(..., min_length=1)
    google_client_secret: str = Field(..., min_length=1)
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = Field(default="HS256", pattern="^(HS256|RS256)$")
    jwt_access_token_expire_minutes: int = Field(default=10080, ge=1, le=10080)
    jwt_refresh_token_expire_minutes: int = Field(default=43200, ge=1, le=43200)
    database_url: str = Field(
        ...,
        description="PostgreSQL database URL (e.g., postgresql://user:password@localhost:5432/dbname)"
    )
    llm_provider: str = Field(
        default="gemini",
        pattern="^(openai|anthropic|gemini)$",
        description="LLM provider: openai, anthropic, or gemini (Gemini 1.5 Flash / 2.0 Flash).",
    )
    llm_api_key: str | None = Field(
        default=None,
        min_length=1,
        description="LLM provider API key (for Gemini use Google AI Studio key). Required for LLM features.",
    )
    llm_model: str = Field(
        default="gemini-1.5-flash",
        description="LLM model: e.g. gpt-4o-mini (openai), gemini-1.5-flash, gemini-2.0-flash (gemini).",
    )
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2000, ge=1, le=8000)
    cors_origins: str = Field(
        default="http://localhost:8081,exp://localhost:8081",
        description="Comma-separated list of allowed CORS origins. Must include http://localhost:8081 for Expo dev server OAuth callback."
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()

