"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    bedrock_vision_model: str = "us.anthropic.claude-sonnet-4-6"
    bedrock_chat_model: str = "us.anthropic.claude-sonnet-4-6"
    bunq_mode: str = "fixture"
    storage_backend: str = "sqlite"
    sqlite_path: str = "/tmp/bunq_nest.db"
    jwt_secret: str = ""
    demo_user_id: str = "u_demo"
    funda_mode: str = "fixture"
    demo_replay: int = 0


settings = Settings()
