"""FastAPI application server"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.routers import documents, insights, training
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="YouTopia Mind API",
    description="Backend API for YouTopia Mind AI Clone Platform",
    version="1.0.0",
)

# Configure CORS
# Allow Vercel frontend and localhost for development
# In production, replace with your actual Vercel domain
import os
cors_origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative dev port
    "http://localhost:5174",  # Alternative Vite port
]

# Add Vercel domains from environment
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
