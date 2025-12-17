"""FastAPI application server"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.routers import documents, insights, training
from src.utils.logging import get_logger
from src.config.settings import settings
from src.utils.environment import (
    log_environment_info,
    validate_environment_config,
    warn_if_production,
    get_environment
)

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="YouTopia Mind API",
    description="Backend API for YouTopia Mind AI Clone Platform",
    version="1.0.0",
)

# Configure CORS
# Allow Vercel frontend and localhost for development
import os
cors_origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative dev port
    "http://localhost:5174",  # Alternative Vite port
    "https://you-topia.ai",  # Production frontend domain
    "https://www.you-topia.ai",  # Production frontend domain with www
]

# Add Vercel domains from environment (for preview deployments)
vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    cors_origins.append(f"https://{vercel_url}")
    cors_origins.append(f"https://*.{vercel_url.split('.', 1)[1] if '.' in vercel_url else vercel_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Log environment and configuration on application startup"""
    env = get_environment()
    
    # Log environment information
    log_environment_info()
    
    # Validate environment configuration
    is_valid, warnings = validate_environment_config()
    
    # Log configuration summary
    logger.info(
        "FastAPI server starting",
        environment=env,
        pinecone_index=settings.pinecone_index_name or "Not set",
        s3_bucket=settings.s3_bucket_name or "Not set",
        config_valid=is_valid,
    )
    
    # Prominent warning if production
    if env == "production":
        logger.warning(
            "=" * 70,
        )
        logger.warning(
            "⚠️  PRODUCTION ENVIRONMENT - API SERVER STARTING",
            environment=env,
            message="All API operations will affect production data"
        )
        logger.warning(
            f"   Pinecone Index: {settings.pinecone_index_name}",
        )
        logger.warning(
            f"   S3 Bucket: {settings.s3_bucket_name}",
        )
        logger.warning(
            "=" * 70,
        )
    
    if warnings:
        logger.warning(
            "Environment configuration warnings detected - review before proceeding",
            warning_count=len(warnings)
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "youtopia-mind-api"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(documents.router, prefix="/api/clone", tags=["documents"])
app.include_router(insights.router, prefix="/api/clone", tags=["insights"])
app.include_router(training.router, prefix="/api/clone", tags=["training"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
