from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""

    # DynamoDB
    dynamo_table: str = "bunq-nest-main"

    # S3
    s3_bucket: str = "bunq-nest-uploads-us-east-1"
    s3_presigned_expiry_seconds: int = 300  # 5 minutes

    # Bedrock model IDs (cross-region inference profiles for us-east-1)
    bedrock_vision_model: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_chat_model: str = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"

    # Cognito
    cognito_user_pool_id: str = ""
    cognito_region: str = "us-east-1"

    # KMS key alias for bunq token encryption
    kms_key_alias: str = "alias/bunq-tokens"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "https://localhost:5173"]


settings = Settings()
