from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "HydroSentinel API"
    database_url: str = "postgresql://malo:Unlimitedphos%401@localhost:5433/hydrosentinel"
    frontend_url: str = "http://localhost:5173"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    admin_email: str = "admin@hydrosentinel.co.za"
    admin_password: str = "admin123"
    admin_password_hash: str | None = None
    model_path: str = "ai/model.pkl"
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        # check both backend/ (Docker) and project root (local dev)
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
