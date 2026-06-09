"""
Vision Detector – Gemini Vision-based product image analysis.

Uses the Gemini Vision API to analyze product images and extract
structured attributes (type, category, material, colors, features)
suitable for e-commerce listing on Amazon India, Flipkart, and Meesho.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from config import settings
from database import get_setting

logger = logging.getLogger("listing_helper.modules.vision_detector")

# Supported image MIME types
_SUPPORTED_MIME_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

# Vision analysis prompt
_VISION_PROMPT = """Analyze this product image carefully. You are a product cataloging expert for Indian e-commerce marketplaces (Amazon India, Flipkart, Meesho).

Return a JSON object with these fields:
{
    "product_type": "the type of product (e.g., baseball cap, water bottle, kitchen organizer)",
    "suggested_name": "a descriptive product name suitable for e-commerce listing",
    "category": "one of: baseball_caps, home_kitchen_general, kitchen_storage, kitchen_tools, home_decor, cleaning_supplies",
    "subcategory": "more specific subcategory",
    "material": "primary material (e.g., cotton, polyester, stainless steel, plastic)",
    "colors": ["list of colors visible in the image"],
    "key_features": ["list of 5-7 key features visible or inferable from the image"],
    "suggested_keywords": ["list of 10-15 search keywords a buyer might use"],
    "confidence": 0.85,
    "suggested_weight_grams": 150,
    "suggested_hsn_code": "65050090"
}

Be specific and accurate. If you cannot determine something, use null.
For suggested_weight_grams: estimate the product weight in grams based on visible size, material, and product type (e.g., a cotton cap ≈ 80–150g, a steel water bottle ≈ 300–500g). Return null if not inferable.
For suggested_hsn_code: return the Indian HSN classification code as a string (e.g., "65050090" for headgear/caps, "7323" for kitchen articles of iron/steel, "3924" for plastic kitchenware). Return null if not confident."""


def _detect_mime_type(image_path: str) -> str:
    """Detect MIME type from file extension.

    Args:
        image_path: Path to the image file.

    Returns:
        MIME type string.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = Path(image_path).suffix.lower()
    mime = _SUPPORTED_MIME_TYPES.get(ext)
    if not mime:
        raise ValueError(
            f"Unsupported image format '{ext}'. "
            f"Supported: {', '.join(_SUPPORTED_MIME_TYPES.keys())}"
        )
    return mime


async def detect_product_from_image(
    image_path: str | None = None,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
) -> dict[str, Any]:
    """Analyze a product image using Gemini Vision API.

    Accepts either a file path or raw bytes. When using ``image_path``
    the MIME type is auto-detected from the extension. When using
    ``image_bytes`` the caller should supply an explicit ``mime_type``.

    Args:
        image_path: Path to an image file on disk.
        image_bytes: Raw image bytes (alternative to image_path).
        mime_type: MIME type of ``image_bytes``. Ignored when
            ``image_path`` is provided.

    Returns:
        Dict of detected product attributes including product_type,
        category, colors, key_features, suggested_keywords, etc.

    Raises:
        ValueError: If neither image source is provided or the API key
            is missing.
        RuntimeError: If the Gemini API call fails.
    """
    api_key = settings.GEMINI_API_KEY or await get_setting("gemini_api_key")
    if not api_key:
        raise ValueError("Gemini API key not configured.")

    # ── Resolve image bytes and MIME type ──────────────────────────
    if image_path:
        path = Path(image_path)
        if not path.is_file():
            raise ValueError(f"Image file not found: {image_path}")
        img_bytes = path.read_bytes()
        mime_type = _detect_mime_type(image_path)
        logger.debug("Read %d bytes from %s", len(img_bytes), image_path)
    elif image_bytes:
        img_bytes = image_bytes
    else:
        raise ValueError("Either image_path or image_bytes must be provided")

    # ── Call Gemini Vision ─────────────────────────────────────────
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                _VISION_PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        logger.info(
            "Vision detection complete: %s (confidence: %s)",
            result.get("product_type", "unknown"),
            result.get("confidence", "N/A"),
        )
        return result

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini response as JSON: %s", exc)
        raise RuntimeError(
            f"Gemini returned invalid JSON. Raw response: {response.text[:200]}"
        ) from exc
    except Exception as exc:
        logger.exception("Gemini Vision API call failed")
        raise RuntimeError(f"Vision detection failed: {exc}") from exc
