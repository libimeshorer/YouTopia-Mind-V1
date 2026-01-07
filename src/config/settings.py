"""Configuration management with environment variables and AWS Secrets Manager"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import boto3
from botocore.exceptions import ClientError


class Settings(BaseSettings):
    """Application settings loaded from environment variables and AWS Secrets Manager"""
    
    # Slack Configuration (optional - only needed for Slack bot)
    slack_bot_token: Optional[str] = Field(None, env="SLACK_BOT_TOKEN")
    slack_signing_secret: Optional[str] = Field(None, env="SLACK_SIGNING_SECRET")
    slack_app_token: Optional[str] = Field(None, env="SLACK_APP_TOKEN")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_embedding_model: str = Field("text-embedding-3-large", env="OPENAI_EMBEDDING_MODEL")
    
    # AWS Configuration (optional - only needed for S3 operations)
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    s3_bucket_name: Optional[str] = Field(None, env="S3_BUCKET_NAME")
    
    # Database (optional - only needed for database operations)
    database_url: Optional[str] = Field(None, env="DATABASE_URL")
    
    # Clerk Authentication (optional - only needed for API server)
    clerk_secret_key: Optional[str] = Field(None, env="CLERK_SECRET_KEY")
    
    # Pinecone Vector Database
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    pinecone_index_name: str = Field("youtopia-dev", env="PINECONE_INDEX_NAME")
    
    # Vector Database (legacy - kept for backward compatibility)
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

    # Chunking Strategy Settings
    chunking_strategy: str = Field("semantic", env="CHUNKING_STRATEGY")  # "semantic" or "recursive"
    semantic_similarity_threshold: float = Field(0.5, env="SEMANTIC_SIMILARITY_THRESHOLD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables (like VITE_* for frontend)


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
    try:
        from dotenv import load_dotenv
        
        # Determine which environment file to load
        # Check ENVIRONMENT variable first (from system env or already loaded)
        env_from_system = os.getenv("ENVIRONMENT", "").lower().strip()
        
        # CRITICAL SAFETY: Default to development if not specified (fail-safe)
        # Only use production if explicitly set to "production" or "prod"
        if not env_from_system:
            env_from_system = "development"
            os.environ["ENVIRONMENT"] = "development"
        
        # Normalize environment values
        if env_from_system in ("dev", "development"):
            env_from_system = "development"
            os.environ["ENVIRONMENT"] = "development"
        elif env_from_system in ("prod", "production"):
            env_from_system = "production"
            os.environ["ENVIRONMENT"] = "production"
        else:
            # Unknown value - default to development for safety
            env_from_system = "development"
            os.environ["ENVIRONMENT"] = "development"
        
        # Priority order:
        # 1. .env.local (if exists) - highest priority for local overrides
        # 2. .dev.env or .prod.env based on ENVIRONMENT variable
        # 3. .env (fallback)
        
        env_file_loaded = False
        
        # First, try .env.local if it exists (for local overrides)
        if os.path.exists(".env.local"):
            load_dotenv(".env.local", override=False)
            env_file_loaded = True
            # Re-check ENVIRONMENT after loading .env.local
            env_from_system = os.getenv("ENVIRONMENT", "").lower().strip()
            # Re-normalize after loading .env.local
            if env_from_system in ("dev", "development"):
                env_from_system = "development"
                os.environ["ENVIRONMENT"] = "development"
            elif env_from_system in ("prod", "production"):
                env_from_system = "production"
                os.environ["ENVIRONMENT"] = "production"
            elif not env_from_system:
                env_from_system = "development"
                os.environ["ENVIRONMENT"] = "development"
        
        # Then load environment-specific file based on ENVIRONMENT variable
        # SAFETY: Default to development if not specified
        if env_from_system == "development":
            if os.path.exists(".dev.env"):
                load_dotenv(".dev.env", override=False)
                env_file_loaded = True
        elif env_from_system == "production":
            if os.path.exists(".prod.env"):
                load_dotenv(".prod.env", override=False)
                env_file_loaded = True
        
        # Fallback to .env if no environment-specific file was loaded
        if not env_file_loaded and os.path.exists(".env"):
            load_dotenv(".env", override=False)
        
        # Handle S3_BUCKET_NAME based on environment
        # If S3_BUCKET_NAME is not set, try S3_BUCKET_NAME_DEV or S3_BUCKET_NAME_PROD
        if not os.getenv("S3_BUCKET_NAME"):
            env_check = os.getenv("ENVIRONMENT", "development").lower()
            if env_check == "development":
                bucket_name = os.getenv("S3_BUCKET_NAME_DEV")
                if bucket_name:
                    os.environ["S3_BUCKET_NAME"] = bucket_name
            elif env_check == "production":
                bucket_name = os.getenv("S3_BUCKET_NAME_PROD")
                if bucket_name:
                    os.environ["S3_BUCKET_NAME"] = bucket_name
                # Fallback to DEV if PROD not found (safety fallback)
                elif os.getenv("S3_BUCKET_NAME_DEV"):
                    os.environ["S3_BUCKET_NAME"] = os.getenv("S3_BUCKET_NAME_DEV")
        
    except ImportError:
        # python-dotenv not available, rely on pydantic-settings default behavior
        pass
    
    # Try to load from environment
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
                settings = Settings()
                return settings
        raise e


# Global settings instance
settings = load_settings()


