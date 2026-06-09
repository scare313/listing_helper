"""
Vision Router – Gemini Vision-based product detection endpoints.

Allows users to upload product images and receive AI-detected
attributes (type, category, colors, features, keywords) for
streamlining product catalog creation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from config import settings
from models import ApiResponse
from modules.vision_detector import detect_product_from_image

logger = logging.getLogger("listing_helper.routers.vision")
router = APIRouter()

# Maximum upload size: 10 MB
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Accepted content types
_ACCEPTED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


@router.post("/detect", response_model=ApiResponse)
async def detect_product(file: UploadFile = File(...)):
    """Upload a product image and detect its attributes using Gemini Vision.

    Accepts JPEG, PNG, and WebP images up to 10 MB. The image is
    analysed by the Gemini Vision model and a structured dict of
    product attributes is returned.

    Args:
        file: Uploaded image file.

    Returns:
        ApiResponse with detected product attributes in ``data``.

    Raises:
        HTTPException 400: Invalid file type or oversized image.
        HTTPException 500: Vision detection failure.
    """
    # ── Validate file type ────────────────────────────────────────
    if file.content_type not in _ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Only JPEG, PNG, and WebP images are supported."
            ),
        )

    # ── Read file contents ────────────────────────────────────────
    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image must be under 10 MB (received {len(contents) / 1024 / 1024:.1f} MB).",
        )

    logger.info(
        "Vision detect requested: filename=%s, size=%d bytes, type=%s",
        file.filename,
        len(contents),
        file.content_type,
    )

    # ── Save to uploads directory for audit trail ─────────────────
    upload_dir = Path(settings.UPLOAD_PATH)
    upload_dir.mkdir(parents=True, exist_ok=True)

    if file.filename:
        save_path = upload_dir / file.filename
        save_path.write_bytes(contents)
        logger.debug("Saved uploaded image to %s", save_path)

    # ── Run vision detection ──────────────────────────────────────
    try:
        result = await detect_product_from_image(
            image_bytes=contents,
            mime_type=file.content_type or "image/jpeg",
        )
        return ApiResponse(
            message="Product detected successfully",
            data=result,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception("Vision detection failed for file %s", file.filename)
        raise HTTPException(
            status_code=500,
            detail=f"Detection failed: {exc}",
        )
