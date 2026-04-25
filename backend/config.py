"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    bedrock_vision_model: str = "us.anthropic.claude-sonnet-4-6"
    bedrock_chat_model: str = "us.anthropic.claude-sonnet-4-6"
    bunq_mode: str = "sandbox"
    bunq_api_key: str = "sandbox_c0ee1158daf5f59bd7325e02b6e17693007b3b5752358f437d293ee1"
    bunq_base_url: str = "https://public-api.sandbox.bunq.com/v1"
    bunq_sandbox: bool = True
    storage_backend: str = "sqlite"
    sqlite_path: str = "/tmp/bunq_nest.db"
    jwt_secret: str = ""
    demo_user_id: str = "u_demo"
    funda_mode: str = ""
    demo_replay: int = 0
    s3_bucket: str = "bunq-nest-uploads-us-east-1"
    s3_presigned_expiry_seconds: int = 300
    dynamo_table: str = "bunq-nest-main"
    cognito_user_pool_id: str = ""
    cognito_region: str = "eu-central-1"


settings = Settings()
