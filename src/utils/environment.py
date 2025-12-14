"""Environment validation and safety utilities"""

import os
from typing import Optional, Callable
from functools import wraps
from src.utils.logging import get_logger

logger = get_logger(__name__)


def get_environment() -> str:
    """
    Get the current environment name.
    
    Returns:
        Environment name: "development", "dev", "production", or "prod"
        Defaults to "development" if not set
    """
    env = os.getenv("ENVIRONMENT", "").lower().strip()
    
    # Normalize environment names
    if env in ("dev", "development"):
        return "development"
    elif env in ("prod", "production"):
        return "production"
    elif env == "":
        # Default to development for safety
        return "development"
    else:
        # Unknown environment - default to development for safety
        logger.warning(f"Unknown environment '{env}', defaulting to 'development'")
        return "development"


def is_production() -> bool:
    """
    Check if current environment is production.
    
    Returns:
        True if environment is production, False otherwise
    """
    return get_environment() == "production"


def is_development() -> bool:
    """
    Check if current environment is development.
    
    Returns:
        True if environment is development, False otherwise
    """
    return get_environment() == "development"


def require_development(operation_name: str = "This operation"):
    """
    Decorator or context manager that requires development environment.
    Raises RuntimeError if called in production.
    
    Args:
        operation_name: Name of the operation for error message
    
    Usage as decorator:
        @require_development("Reset operation")
        def reset():
            ...
    
    Usage as context manager:
        with require_development("Data deletion"):
            delete_all_data()
    """
    class DevelopmentRequired:
        def __init__(self, op_name: str):
            self.op_name = op_name
        
        def __enter__(self):
            if is_production():
                raise RuntimeError(
                    f"{self.op_name} is not allowed in production environment. "
                    f"Current environment: {get_environment()}. "
                    "Set ENVIRONMENT=development to run this operation."
                )
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            return False
        
        def __call__(self, func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if is_production():
                    raise RuntimeError(
                        f"{self.op_name} is not allowed in production environment. "
                        f"Current environment: {get_environment()}. "
                        "Set ENVIRONMENT=development to run this operation."
                    )
                return func(*args, **kwargs)
            return wrapper
    
    return DevelopmentRequired(operation_name)


def warn_if_production(message: Optional[str] = None) -> bool:
    """
    Log a warning if running in production environment.
    
    Args:
        message: Optional custom warning message
    
    Returns:
        True if production environment detected, False otherwise
    """
    if is_production():
        warning_msg = message or "Running in PRODUCTION environment"
        logger.warning(
            f"⚠️  {warning_msg}",
            environment=get_environment(),
            additional_context="Double-check all operations are safe for production"
        )
        return True
    return False


def validate_environment_config() -> tuple[bool, list[str]]:
    """
    Validate that configuration matches the current environment.
    Checks resource names (Pinecone index, S3 bucket) match environment expectations.
    
    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    # Lazy import to avoid circular dependency
    from src.config.settings import settings
    
    warnings = []
    env = get_environment()
    
    # Check Pinecone index name
    index_name = settings.pinecone_index_name
    if index_name:
        if env == "production":
            if "prod" not in index_name.lower() and "dev" in index_name.lower():
                warnings.append(
                    f"Pinecone index name '{index_name}' contains 'dev' but environment is production. "
                    "Expected index name to contain 'prod' for production environment."
                )
        elif env == "development":
            if "prod" in index_name.lower() and "dev" not in index_name.lower():
                warnings.append(
                    f"Pinecone index name '{index_name}' contains 'prod' but environment is development. "
                    "Expected index name to contain 'dev' for development environment."
                )
    
    # Check S3 bucket name
    bucket_name = settings.s3_bucket_name
    if bucket_name:
        if env == "production":
            if "prod" not in bucket_name.lower() and "dev" in bucket_name.lower():
                warnings.append(
                    f"S3 bucket name '{bucket_name}' contains 'dev' but environment is production. "
                    "Expected bucket name to contain 'prod' for production environment."
                )
        elif env == "development":
            if "prod" in bucket_name.lower() and "dev" not in bucket_name.lower():
                warnings.append(
                    f"S3 bucket name '{bucket_name}' contains 'prod' but environment is development. "
                    "Expected bucket name to contain 'dev' for development environment."
                )
    
    # Check database URL
    db_url = settings.database_url
    if db_url:
        # Check for obvious mismatches (this is heuristic-based)
        db_url_lower = db_url.lower()
        if env == "production":
            if "localhost" in db_url_lower or "127.0.0.1" in db_url_lower:
                warnings.append(
                    "Database URL contains localhost/127.0.0.1 but environment is production. "
                    "Expected production database URL (e.g., Render PostgreSQL)."
                )
        elif env == "development":
            # Less strict for dev - localhost is fine
            pass
    
    is_valid = len(warnings) == 0
    
    if warnings:
        logger.warning(
            "Environment configuration validation found issues",
            environment=env,
            warnings=warnings
        )
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    return is_valid, warnings


def log_environment_info():
    """
    Log current environment and key configuration values.
    Should be called at application startup.
    """
    # Lazy import to avoid circular dependency
    from src.config.settings import settings
    
    env = get_environment()
    
    # Mask sensitive values
    db_url = settings.database_url or "Not set"
    if db_url != "Not set" and "://" in db_url:
        # Mask password in database URL
        try:
            parts = db_url.split("://")
            if len(parts) == 2 and "@" in parts[1]:
                # Has credentials
                scheme = parts[0]
                rest = parts[1]
                if "/" in rest:
                    host_part, db_part = rest.split("/", 1)
                    if ":" in host_part and "@" in host_part:
                        # Has user:pass@host
                        user_pass, host = host_part.rsplit("@", 1)
                        masked = f"{scheme}://***:***@{host}/{db_part}"
                    else:
                        masked = f"{scheme}://{host_part}/{db_part}"
                else:
                    masked = f"{scheme}://***:***@{rest}"
            else:
                masked = db_url
        except Exception:
            masked = "*** (error parsing)"
    else:
        masked = db_url
    
    logger.info(
        "Environment Configuration",
        environment=env,
        pinecone_index=settings.pinecone_index_name or "Not set",
        s3_bucket=settings.s3_bucket_name or "Not set",
        database_url=masked,
    )
    
    if is_production():
        logger.warning(
            "⚠️  PRODUCTION ENVIRONMENT DETECTED",
            environment=env,
            message="All operations will affect production data. Exercise extreme caution."
        )
