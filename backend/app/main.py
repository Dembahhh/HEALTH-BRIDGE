"""
Health-bridge AI - FastAPI Application

Main entry point for the FastAPI application.
"""

from dotenv import load_dotenv
load_dotenv()  # populate os.environ from .env before any other imports

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config.settings import settings
from app.config.database import init_db, close_db, get_database
from app.api.routes import chat, profile, plans
from app.core.rate_limit import limiter

# Configure logging so INFO messages from our app show in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

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

    # Pre-initialize the LLM extractor + semantic matcher at startup
    # so the first chat request isn't delayed by ~40s of model loading
    try:
        from app.services.llm_extractor import get_extractor
        import asyncio
        await asyncio.get_event_loop().run_in_executor(None, get_extractor, True)
        logger.info("LLM Extractor pre-initialized")
    except Exception as e:
        logger.warning("LLM Extractor pre-init failed (will init on first request): %s", e)

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
        allow_origins=settings.get_cors_origins(),
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
