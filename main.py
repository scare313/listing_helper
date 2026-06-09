"""
Listing Helper – FastAPI Application Entry Point.

E-commerce listing management tool for Amazon India, Flipkart, and Meesho.
Provides AI-powered content generation, keyword research, pricing
calculations, and bulk template exports.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("listing_helper")

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events.

    Startup:
        - Initialise the SQLite database (create tables if needed).
        - Ensure the exports directory exists.

    Shutdown:
        - (reserved for future cleanup)
    """
    logger.info("🚀 Starting Listing Helper v1.0.0")

    # Ensure data directories
    export_dir = Path(settings.EXPORT_PATH)
    export_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Export directory ready: %s", export_dir.resolve())

    # Initialise database
    await init_db()

    yield  # ── application is running ──

    logger.info("👋 Shutting down Listing Helper")


# ---------------------------------------------------------------------------
# Application Instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Listing Helper",
    description=(
        "AI-powered product listing management for Amazon India, Flipkart, "
        "and Meesho. Automates content generation, keyword research, pricing "
        "calculations, and bulk template exports."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware (allow everything for local development)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from routers.products import router as products_router     # noqa: E402
from routers.keywords import router as keywords_router     # noqa: E402
from routers.content import router as content_router       # noqa: E402
from routers.templates import router as templates_router   # noqa: E402
from routers.pricing import router as pricing_router       # noqa: E402
from routers.vision import router as vision_router         # noqa: E402
from routers.settings import router as settings_router       # noqa: E402

app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(keywords_router, prefix="/api/keywords", tags=["Keywords"])
app.include_router(content_router, prefix="/api/content", tags=["Content"])
app.include_router(templates_router, prefix="/api/templates", tags=["Templates"])
app.include_router(pricing_router, prefix="/api/pricing", tags=["Pricing"])
app.include_router(vision_router, prefix="/api/vision", tags=["Vision"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])

# ---------------------------------------------------------------------------
# Static Files (serve frontend)
# ---------------------------------------------------------------------------

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info("Static files mounted from %s", static_dir)
else:
    logger.warning("Static directory not found at %s – frontend will not be served", static_dir)

# ---------------------------------------------------------------------------
# Root & Health
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    """Serve the frontend index.html."""
    index = static_dir / "index.html"
    if index.is_file():
        return FileResponse(str(index))
    return JSONResponse(
        content={"message": "Listing Helper API v1.0.0 – frontend not yet built"},
        status_code=200,
    )


@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint.

    Returns:
        JSON with status, version, and database path.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": settings.DATABASE_PATH,
        "export_path": settings.EXPORT_PATH,
    }


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler that returns a structured error response."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc),
        },
    )


# ---------------------------------------------------------------------------
# Entry Point (direct run)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
        log_level="info",
    )
