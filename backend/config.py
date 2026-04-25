"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    bunq_mode: str = "fixture"
    storage_backend: str = "sqlite"
    sqlite_path: str = "/tmp/bunq_nest.db"
    jwt_secret: str = ""
    demo_user_id: str = "u_demo"
    funda_mode: str = "fixture"
    demo_replay: int = 0


settings = Settings()
