"""FastAPI application server"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.routers import documents, insights, training, integrations, chat, agent
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
    title="YouTopia Mind FastAPI app",
    description="Backend API for YouTopia Mind AI Clone Platform",
    version="1.0.0",
)

# Configure CORS
# Allow Vercel frontend and localhost for development
import os

# Determine environment
env = os.getenv("ENVIRONMENT", "development").lower()

cors_origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative dev port
    "http://localhost:5174",  # Alternative Vite port
    "http://localhost:8080",  # Vite default port
    "https://you-topia.ai",  # Production frontend domain
    "https://www.you-topia.ai",  # Production frontend domain with www
]

# Add Vercel domains from environment (for preview deployments)
vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    cors_origins.append(f"https://{vercel_url}")

# For development environment, allow all Vercel preview deployments using regex
cors_origin_regex = None
if env in ("dev", "development"):
    # Allow all Vercel preview deployments (e.g., https://you-topia-git-*.vercel.app)
    cors_origin_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTPException handler with CORS headers"""
    logger.warning("HTTPException", status_code=exc.status_code, detail=exc.detail, path=request.url.path)
    
    # Get origin from request
    origin = request.headers.get("origin")
    
    # Build response
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    
    # Add CORS headers if origin is in allowed origins
    if origin and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with CORS headers"""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    
    # Get origin from request
    origin = request.headers.get("origin")
    
    # Build response
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
    
    # Add CORS headers if origin is in allowed origins
    if origin and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


# Include routers
app.include_router(documents.router, prefix="/api/clone", tags=["documents"])
app.include_router(insights.router, prefix="/api/clone", tags=["insights"])
app.include_router(training.router, prefix="/api/clone", tags=["training"])
app.include_router(integrations.router, prefix="/api/clone", tags=["integrations"])
app.include_router(chat.router, prefix="/api/clone", tags=["chat"])
app.include_router(agent.router, prefix="/api/clone", tags=["agent"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
