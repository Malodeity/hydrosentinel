# Settings read from environment variables (the .env file). Anything that differs between a laptop and a server lives here: database address,
# JWT secret, admin seed credentials, OpenAI key, model file path. get_settings() is cached, so the file is parsed once.

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "HydroSentinel API"
    database_url: str = "postgresql://postgres:change-me@localhost:5432/hydrosentinel"
    frontend_url: str = "http://localhost:5173"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    admin_email: str = "admin@hydrosentinel.co.za"
    admin_password: str = "admin123"
    admin_password_hash: str | None = None
    model_path: str = "ai/model.pkl"
    openai_api_key: str | None = None
    # optional mail server: with smtp_host empty, notifications stay in the app (the bell) and no email is sent
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@hydrosentinel.co.za"
    # demo contractors and logins are created at start only when this is true. leave it off outside a demo
    seed_demo_data: bool = False
    # password for the demo contractor logins (demo data only)
    demo_contractor_password: str = "contractor123"

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
