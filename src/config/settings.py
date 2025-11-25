"""Configuration management with environment variables and AWS Secrets Manager"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import boto3
from botocore.exceptions import ClientError


class Settings(BaseSettings):
    """Application settings loaded from environment variables and AWS Secrets Manager"""
    
    # Slack Configuration
    slack_bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    slack_signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")
    slack_app_token: Optional[str] = Field(None, env="SLACK_APP_TOKEN")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_embedding_model: str = Field("text-embedding-3-small", env="OPENAI_EMBEDDING_MODEL")
    
    # AWS Configuration
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    s3_bucket_name: str = Field(..., env="S3_BUCKET_NAME")
    
    # Vector Database
    chroma_db_path: str = Field("./data/chroma_db", env="CHROMA_DB_PATH")
    chroma_persist_directory: str = Field("./data/chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    
    # Application Settings
    log_level: str = Field("INFO", env="LOG_LEVEL")
    environment: str = Field("development", env="ENVIRONMENT")
    
    # Personality Profile
    personality_profile_path: str = Field("./data/personality_profile.json", env="PERSONALITY_PROFILE_PATH")
    
    # RAG Settings
    max_context_tokens: int = Field(4000, env="MAX_CONTEXT_TOKENS")
    top_k_retrieval: int = Field(5, env="TOP_K_RETRIEVAL")
    chunk_size: int = Field(1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(200, env="CHUNK_OVERLAP")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_secret_from_aws(secret_name: str, region_name: str = "us-east-1") -> Optional[dict]:
    """Retrieve secret from AWS Secrets Manager"""
    try:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        import json
        return json.loads(get_secret_value_response["SecretString"])
    except ClientError as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        return None


def load_settings() -> Settings:
    """Load settings from environment variables, with optional AWS Secrets Manager fallback"""
    # Try to load from environment first
    try:
        settings = Settings()
        return settings
    except Exception as e:
        # If critical secrets are missing, try AWS Secrets Manager
        if os.getenv("AWS_SECRETS_NAME"):
            secrets = get_secret_from_aws(os.getenv("AWS_SECRETS_NAME"), os.getenv("AWS_REGION", "us-east-1"))
            if secrets:
                # Update environment with secrets
                for key, value in secrets.items():
                    os.environ[key.upper()] = str(value)
                return Settings()
        raise e


# Global settings instance
settings = load_settings()

