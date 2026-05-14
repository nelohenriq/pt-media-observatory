"""Main entry point for PT Media Observatory FastAPI application."""
import logging
from fastapi import FastAPI
from .config import Settings
from .database import engine
from .api.auth import router as auth_router
from .api import submissions, events

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pt-media-observatory")

# Load settings
settings = Settings()

# Create FastAPI app
app = FastAPI(
    title="PT Media Observatory Backend",
    version="0.1.0",
    description="Backend for PT Media Observatory - v1 implementation",
    root_path="/",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Include routers
app.include_router(auth_router, prefix="/auth")
app.include_router(submissions.router, prefix="/submissions")
app.include_router(events.router, prefix="/events")

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "namespace": settings.project_namespace}


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize DB tables on startup (development only)."""
    logger.info("Starting PT Media Observatory backend")
    logger.info(f"Running on port {settings.port}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down PT Media Observatory backend")