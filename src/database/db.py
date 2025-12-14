"""Database connection and session management"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from src.config.settings import settings
from src.utils.logging import get_logger
from src.utils.environment import get_environment, warn_if_production

logger = get_logger(__name__)

# Log environment and database connection info
env = get_environment()

# Mask database URL for logging
db_url = settings.database_url or "Not set"
if db_url != "Not set" and "://" in db_url:
    try:
        # Extract just the host/database part for logging (mask credentials)
        parts = db_url.split("://")
        if len(parts) == 2:
            scheme = parts[0]
            rest = parts[1]
            if "/" in rest:
                host_part, db_part = rest.split("/", 1)
                if "@" in host_part:
                    # Has credentials - mask them
                    _, host = host_part.rsplit("@", 1)
                    masked_url = f"{scheme}://***:***@{host}/{db_part}"
                else:
                    masked_url = f"{scheme}://{host_part}/{db_part}"
            else:
                if "@" in rest:
                    _, host = rest.rsplit("@", 1)
                    masked_url = f"{scheme}://***:***@{host}"
                else:
                    masked_url = db_url
        else:
            masked_url = "***"
    except Exception:
        masked_url = "*** (error parsing)"
else:
    masked_url = db_url

logger.info(
    "Database connection initializing",
    environment=env,
    database_url=masked_url,
)

# Warn if production
if env == "production":
    # Check if connecting to localhost in production (suspicious)
    if db_url and ("localhost" in db_url.lower() or "127.0.0.1" in db_url.lower()):
        logger.error(
            "⚠️  PRODUCTION ENVIRONMENT: Database URL contains localhost/127.0.0.1!",
            environment=env,
            database_url_masked=masked_url,
            message="This may indicate a configuration error. Production should use remote database (e.g., Render PostgreSQL)."
        )
    else:
        logger.warning(
            "⚠️  PRODUCTION ENVIRONMENT: Connecting to production database",
            environment=env,
            database_url_masked=masked_url,
            message="All database operations will affect production data. Exercise extreme caution."
        )

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10,
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create all tables)"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def get_db_session() -> Session:
    """
    Get a database session (for use outside FastAPI dependencies).
    Remember to close it when done: session.close()
    """
    return SessionLocal()
