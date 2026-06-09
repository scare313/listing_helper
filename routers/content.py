"""
Content Router – Endpoints for calling Gemini AI content generator and saving marketplace drafts.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database import get_product, get_variations, update_product, save_variation_content
from models import ApiResponse, ContentGenerationRequest, ContentGenerationResponse, MarketplaceContent
from modules.content_generator import (
    generate_marketplace_content,
    generate_content_with_variations,
    validate_content,
)

logger = logging.getLogger("listing_helper.routers.content")
router = APIRouter()


# ============================================================================
# Request Schemas (router-local)
# ============================================================================

class GenerateWithVariationsRequest(BaseModel):
    """Request body for generating content for a product and all its variations."""

    product_id: int = Field(..., description="Product ID to generate content for")
    keywords: list[str] = Field(default_factory=list, description="Target keywords to inject")
    marketplace: str = Field("all", pattern="^(amazon|flipkart|meesho|all)$")


class ValidateContentRequest(BaseModel):
    """Request body for validating marketplace content against character limits."""

    marketplace: str = Field(..., pattern="^(amazon|flipkart|meesho)$")
    title: str = ""
    bullets: list[str] = Field(default_factory=list)
    description: str = ""
    keywords: str = ""


# ============================================================================
# Helper – save ContentGenerationResponse to product record
# ============================================================================

async def _save_content_to_product(
    product_id: int,
    response: ContentGenerationResponse,
) -> None:
    """Persist generated marketplace content back into the products table.

    Args:
        product_id: Product primary key.
        response: Generated content for one or more marketplaces.
    """
    update_data: dict[str, Any] = {}

    if response.amazon:
        update_data.update({
            "amazon_title": response.amazon.title,
            "amazon_bullets": response.amazon.bullets or [],
            "amazon_description": response.amazon.description,
            "amazon_search_terms": response.amazon.search_terms,
            "amazon_status": "ready",
        })

    if response.flipkart:
        update_data.update({
            "flipkart_title": response.flipkart.title,
            "flipkart_key_features": response.flipkart.key_features or [],
            "flipkart_description": response.flipkart.description,
            "flipkart_search_keywords": response.flipkart.keywords,
            "flipkart_status": "ready",
        })

    if response.meesho:
        update_data.update({
            "meesho_title": response.meesho.title,
            "meesho_description": response.meesho.description,
            "meesho_status": "ready",
        })

    if update_data:
        await update_product(product_id, update_data)
        logger.info("Saved generated drafts back to product id=%d", product_id)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/generate", response_model=ApiResponse)
async def generate_content(body: ContentGenerationRequest):
    """Generate e-commerce listings for one or more marketplaces.

    Loads the product specifications and its applied keywords from the DB,
    passes them into Gemini structured prompts, and saves the output copy back
    into the product record as drafts.

    Args:
        body: Product ID, target marketplace, and optional manual seed keywords.

    Returns:
        Structured marketplace drafts.
    """
    logger.info("Content generation requested: product_id=%s, marketplace=%s", body.product_id, body.marketplace)

    product_id = body.product_id
    product_details = {}
    keywords = body.keywords or []

    # 1. Fetch specs and applied keywords from DB if product ID is supplied
    if product_id:
        product = await get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

        product_details = product

        # Load applied keywords if they exist and none were manually passed in body
        if not keywords and product.get("keywords_data"):
            keywords_dict = product["keywords_data"]
            if isinstance(keywords_dict, dict):
                keywords = keywords_dict.get("applied_keywords", [])
    else:
        # Standalone sandbox generation (no product ID)
        if body.product_details:
            product_details = body.product_details
        else:
            raise HTTPException(
                status_code=400,
                detail="Either product_id or product_details must be provided",
            )

    # 2. Invoke Gemini content generator
    try:
        response: ContentGenerationResponse = await generate_marketplace_content(
            product_details=product_details,
            keywords=keywords,
            marketplace=body.marketplace,
        )
    except ValueError as exc:
        # API key not configured – return 400 with clear message
        logger.warning("Content generation blocked: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        logger.error("Content generation runtime error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to generate content")
        raise HTTPException(status_code=500, detail=str(exc))

    # 3. If product_id exists, automatically save the generated copy back as drafts
    if product_id:
        await _save_content_to_product(product_id, response)

    return ApiResponse(
        message="Content generated and saved successfully",
        data=response.model_dump(exclude_none=True),
    )


@router.post("/generate/all", response_model=ApiResponse)
async def generate_all_content(body: ContentGenerationRequest):
    """Convenience wrapper that forces marketplace='all' to write all drafts at once."""
    body.marketplace = "all"
    return await generate_content(body)


@router.post("/generate-with-variations", response_model=ApiResponse)
async def generate_with_variations(body: GenerateWithVariationsRequest):
    """Generate content for a base product and all its variations.

    Reads the product and all associated variations from the database,
    generates base content for all 3 marketplaces, then generates adapted
    content for each variation. Saves base content to the product record
    and variation content to the variation_content table.

    Args:
        body: Product ID, keywords, and target marketplace.

    Returns:
        Dict with ``base`` content and ``variations`` keyed by variation ID.
    """
    logger.info(
        "Variation-aware content generation requested: product_id=%d",
        body.product_id,
    )

    # 1. Fetch product
    product = await get_product(body.product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID {body.product_id} not found",
        )

    # 2. Resolve keywords
    keywords = body.keywords or []
    if not keywords and product.get("keywords_data"):
        keywords_dict = product["keywords_data"]
        if isinstance(keywords_dict, dict):
            keywords = keywords_dict.get("applied_keywords", [])

    # 3. Fetch all variations
    variations = await get_variations(body.product_id)
    if not variations:
        raise HTTPException(
            status_code=404,
            detail=f"No variations found for product ID {body.product_id}. "
                   "Use /generate endpoint for products without variations.",
        )

    # 4. Generate content
    try:
        result = await generate_content_with_variations(
            product_details=product,
            keywords=keywords,
            variations=variations,
        )
    except ValueError as exc:
        logger.warning("Content generation blocked: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        logger.error("Content generation runtime error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to generate content with variations")
        raise HTTPException(status_code=500, detail=str(exc))

    # 5. Save base content to product record
    base_content: ContentGenerationResponse = result["base"]
    await _save_content_to_product(body.product_id, base_content)

    # 6. Save each variation's content to variation_content table
    variation_contents: dict[int, ContentGenerationResponse] = result["variations"]
    for var_id, var_response in variation_contents.items():
        for mp_name in ("amazon", "flipkart", "meesho"):
            mp_content: MarketplaceContent | None = getattr(var_response, mp_name, None)
            if mp_content is None:
                continue

            content_data: dict[str, Any] = {
                "title": mp_content.title,
                "description": mp_content.description,
                "status": "ready",
            }

            # Store bullets/features as the 'bullets' field
            if mp_name == "amazon" and mp_content.bullets:
                content_data["bullets"] = mp_content.bullets
            elif mp_name == "flipkart" and mp_content.key_features:
                content_data["bullets"] = mp_content.key_features

            # Store keywords/search_terms in the 'keywords' field
            if mp_name == "amazon" and mp_content.search_terms:
                content_data["keywords"] = mp_content.search_terms
            elif mp_name == "flipkart" and mp_content.keywords:
                content_data["keywords"] = mp_content.keywords

            await save_variation_content(var_id, mp_name, content_data)

    logger.info(
        "Saved variation content for product id=%d (%d variations)",
        body.product_id, len(variation_contents),
    )

    # 7. Build serialisable response
    serialised_variations = {}
    for var_id, var_resp in variation_contents.items():
        serialised_variations[str(var_id)] = var_resp.model_dump(exclude_none=True)

    return ApiResponse(
        message=f"Content generated for base product and {len(variations)} variations",
        data={
            "base": base_content.model_dump(exclude_none=True),
            "variations": serialised_variations,
        },
    )


@router.post("/validate", response_model=ApiResponse)
async def validate_marketplace_content(body: ValidateContentRequest):
    """Validate listing content against marketplace character limits.

    Accepts raw content fields and checks each against the limits defined
    in ``MARKETPLACE_LIMITS``.

    Args:
        body: Marketplace name and content fields to validate.

    Returns:
        List of validation results per field.
    """
    logger.info("Content validation requested for marketplace: %s", body.marketplace)

    # Build a MarketplaceContent object from the request
    content = MarketplaceContent(
        title=body.title,
        description=body.description,
    )

    # Assign marketplace-specific list fields
    if body.marketplace == "amazon":
        content.bullets = body.bullets if body.bullets else None
        content.search_terms = body.keywords if body.keywords else None
    elif body.marketplace == "flipkart":
        content.key_features = body.bullets if body.bullets else None
        content.keywords = body.keywords if body.keywords else None

    validation_results = validate_content(content, body.marketplace)

    # Determine overall validity
    all_valid = all(r["is_valid"] for r in validation_results)

    return ApiResponse(
        message="All fields within limits" if all_valid else "Some fields exceed marketplace limits",
        data={
            "marketplace": body.marketplace,
            "all_valid": all_valid,
            "fields": validation_results,
        },
    )
