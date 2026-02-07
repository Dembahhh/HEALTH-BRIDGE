"""
Health-bridge AI - FastAPI Application

Main entry point for the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.config.database import init_db, close_db, get_database
from app.api.routes import chat, profile, plans
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Health-bridge AI...")

    # Initialize Firebase
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized")
    except Exception as e:
        logger.warning("Firebase initialization failed: %s", e)

    await init_db()
    logger.info("Database connected")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database disconnected")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Health-bridge AI",
        description="Preventive health coach for hypertension and diabetes risk in low-resource African settings",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # Include routers
    app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
    app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
    app.include_router(plans.router, prefix="/api/plans", tags=["Plans"])

    # Health check with MongoDB ping
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint with database connectivity verification."""
        db_status = "unknown"
        try:
            db = get_database()
            await db.command("ping")
            db_status = "connected"
        except Exception as e:
            logger.warning("Health check DB ping failed: %s", e)
            db_status = "disconnected"

        status = "healthy" if db_status == "connected" else "degraded"
        return {
            "status": status,
            "service": "health-bridge-ai",
            "version": "0.1.0",
            "database": db_status,
        }

    # ChromaDB health check endpoint
    @app.get("/health/chromadb", tags=["Health"])
    async def health_chromadb():
        """
        Check ChromaDB connectivity.
        
        Note: This creates a new SemanticMemory instance on each call.
        For production with frequent health checks, consider implementing
        a cached connection test or singleton pattern.
        """
        try:
            from app.core.memory.semantic_memory import SemanticMemory
            memory = SemanticMemory()
            # Try a simple operation
            stats = memory.collection.count()
            return {"status": "healthy", "documents": stats}
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": str(e)}
            )

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API info."""
        return {
            "message": "Welcome to Health-bridge AI",
            "docs": "/docs",
            "health": "/health",
        }

    return app


# Create app instance
app = create_app()
