"""
Settings Router – App configuration and API key validation endpoints.

Provides endpoints to read/write app-level settings stored in the
``app_settings`` table and to validate Gemini API keys.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from google import genai

from config import settings
from database import get_all_settings, get_setting, set_setting
from models import ApiResponse

logger = logging.getLogger("listing_helper.routers.settings")
router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_settings():
    """Get all app settings.

    Merges database-stored settings with built-in defaults so that
    the response always contains a complete picture.

    Returns:
        ApiResponse with a dict of key→value settings in ``data``.
    """
    db_settings = await get_all_settings()

    # Merge with defaults
    defaults: dict[str, str] = {
        "gemini_api_key_configured": str(bool(settings.GEMINI_API_KEY)),
        "gemini_model": settings.GEMINI_MODEL,
        "default_margin": str(settings.DEFAULT_TARGET_MARGIN),
        "headless_browser": str(settings.HEADLESS_BROWSER),
        "scraper_min_delay": str(settings.SCRAPER_MIN_DELAY),
        "scraper_max_delay": str(settings.SCRAPER_MAX_DELAY),
        "export_path": settings.EXPORT_PATH,
        "upload_path": settings.UPLOAD_PATH,
    }
    defaults.update(db_settings)

    return ApiResponse(data=defaults)


@router.put("/{key}", response_model=ApiResponse)
async def update_setting(key: str, value: str):
    """Update a single app setting.

    Args:
        key: Setting key.
        value: New value.

    Returns:
        ApiResponse confirming the update.
    """
    await set_setting(key, value)
    logger.info("Setting updated: %s", key)
    return ApiResponse(message=f"Setting '{key}' updated successfully")


@router.get("/{key}", response_model=ApiResponse)
async def read_setting(key: str):
    """Read a single app setting.

    Args:
        key: Setting key.

    Returns:
        ApiResponse with the setting value in ``data``.

    Raises:
        HTTPException 404: If the setting does not exist.
    """
    value = await get_setting(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return ApiResponse(data={"key": key, "value": value})


@router.post("/test-gemini", response_model=ApiResponse)
async def test_gemini_key(api_key: str | None = None):
    """Test if a Gemini API key is valid.

    Sends a minimal prompt to the configured Gemini model and checks
    for a successful response. Uses the provided key or falls back to
    the environment-configured key.

    Args:
        api_key: Optional API key to test. Falls back to
            ``settings.GEMINI_API_KEY``.

    Returns:
        ApiResponse with a truncated model response in ``data``.

    Raises:
        HTTPException 400: If no key is available or the key is invalid.
    """
    key = api_key or settings.GEMINI_API_KEY
    if not key:
        raise HTTPException(
            status_code=400,
            detail="No API key provided and no key configured in environment.",
        )

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="Say OK",
        )
        return ApiResponse(
            message="API key is valid",
            data={"response": response.text[:100]},
        )
    except Exception as exc:
        logger.warning("Gemini API key validation failed: %s", exc)
        raise HTTPException(
            status_code=400,
            detail=f"API key validation failed: {exc}",
        )
