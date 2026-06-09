"""
Products Router – Full CRUD for product management.

Endpoints:
    GET    /                                  List products (filtered, paginated)
    GET    /stats/overview                    Dashboard stats
    GET    /{product_id}                      Get single product
    POST   /                                  Create product
    PUT    /{product_id}                      Update product (partial)
    DELETE /{product_id}                      Delete product
    GET    /{product_id}/variations           List variations
    POST   /{product_id}/variations           Add variation
    DELETE /{product_id}/variations/{var_id}  Delete variation
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database import (
    create_product,
    create_variation,
    delete_product,
    delete_variation,
    get_all_products,
    get_dashboard_stats,
    get_product,
    get_variations,
    update_product,
)
from models import (
    ApiResponse,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    VariationCreate,
    VariationResponse,
)

logger = logging.getLogger("listing_helper.routers.products")
router = APIRouter()


# ============================================================================
# List / Search
# ============================================================================

@router.get("/", response_model=ApiResponse)
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(
        None,
        description="Filter by marketplace status, format: marketplace:status (e.g. amazon:draft)",
    ),
    search: Optional[str] = Query(None, description="Free-text search across name, sku, brand"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
):
    """List all products with optional filters and pagination.

    Supports filtering by category, marketplace status, and free-text
    search. Results are ordered by most recently updated first.
    """
    products, total = await get_all_products(
        category=category,
        marketplace_status=status,
        search=search,
        page=page,
        per_page=per_page,
    )
    return ApiResponse(
        data=ProductListResponse(
            products=[ProductResponse(**p) for p in products],
            total=total,
            page=page,
            per_page=per_page,
        )
    )


# ============================================================================
# Dashboard Stats  (must be BEFORE /{product_id} to avoid route conflict)
# ============================================================================

@router.get("/stats/overview", response_model=ApiResponse)
async def product_stats():
    """Dashboard overview statistics.

    Returns total product count, per-marketplace status breakdowns,
    and the 10 most recently updated products.
    """
    stats = await get_dashboard_stats()
    return ApiResponse(data=stats)


# ============================================================================
# Single Product
# ============================================================================

@router.get("/{product_id}", response_model=ApiResponse)
async def get_single_product(product_id: int):
    """Retrieve a single product by ID, including its variations.

    Args:
        product_id: The product primary key.

    Raises:
        HTTPException 404: If the product does not exist.
    """
    product = await get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    variations = await get_variations(product_id)
    product_resp = ProductResponse(**product)
    return ApiResponse(
        data={
            "product": product_resp.model_dump(),
            "variations": [VariationResponse(**v).model_dump() for v in variations],
        }
    )


# ============================================================================
# Create
# ============================================================================

@router.post("/", response_model=ApiResponse, status_code=201)
async def create_new_product(body: ProductCreate):
    """Create a new product.

    The SKU must be unique. All marketplace fields default to draft
    status with empty content.

    Args:
        body: Product creation payload.

    Raises:
        HTTPException 409: If a product with the same SKU already exists.
    """
    try:
        product = await create_product(body.model_dump())
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(
                status_code=409,
                detail=f"A product with SKU '{body.sku}' already exists",
            )
        logger.exception("Failed to create product")
        raise HTTPException(status_code=500, detail="Failed to create product")

    logger.info("Created product: %s (SKU: %s)", body.name, body.sku)
    return ApiResponse(
        message="Product created successfully",
        data=ProductResponse(**product).model_dump(),
    )


# ============================================================================
# Update
# ============================================================================

@router.put("/{product_id}", response_model=ApiResponse)
async def update_existing_product(product_id: int, body: ProductUpdate):
    """Partially update a product.

    Only fields included in the request body are updated. Fields set
    to ``null`` / not included are left unchanged.

    Args:
        product_id: Product primary key.
        body: Fields to update.

    Raises:
        HTTPException 404: If the product does not exist.
    """
    existing = await get_product(product_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return ApiResponse(
            message="No fields to update",
            data=ProductResponse(**existing).model_dump(),
        )

    updated = await update_product(product_id, update_data)
    logger.info("Updated product id=%d fields=%s", product_id, list(update_data.keys()))
    return ApiResponse(
        message="Product updated successfully",
        data=ProductResponse(**updated).model_dump(),
    )


# ============================================================================
# Delete
# ============================================================================

@router.delete("/{product_id}", response_model=ApiResponse)
async def delete_existing_product(product_id: int):
    """Delete a product and all its associated variations.

    Args:
        product_id: Product primary key.

    Raises:
        HTTPException 404: If the product does not exist.
    """
    deleted = await delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    logger.info("Deleted product id=%d", product_id)
    return ApiResponse(message="Product deleted successfully")


# ============================================================================
# Variations
# ============================================================================

@router.get("/{product_id}/variations", response_model=ApiResponse)
async def list_variations(product_id: int):
    """List all variations for a product.

    Args:
        product_id: Product primary key.

    Raises:
        HTTPException 404: If the parent product does not exist.
    """
    product = await get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    variations = await get_variations(product_id)
    return ApiResponse(
        data=[VariationResponse(**v).model_dump() for v in variations]
    )


@router.post("/{product_id}/variations", response_model=ApiResponse, status_code=201)
async def add_variation(product_id: int, body: VariationCreate):
    """Add a variation to an existing product.

    Args:
        product_id: Product primary key.
        body: Variation data.

    Raises:
        HTTPException 404: If the parent product does not exist.
    """
    product = await get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    variation = await create_variation(product_id, body.model_dump())
    logger.info("Added variation %s=%s to product id=%d", body.variation_type, body.variation_value, product_id)
    return ApiResponse(
        message="Variation added successfully",
        data=VariationResponse(**variation).model_dump(),
    )


@router.delete("/{product_id}/variations/{variation_id}", response_model=ApiResponse)
async def remove_variation(product_id: int, variation_id: int):
    """Delete a specific variation.

    Args:
        product_id: Product primary key (for URL consistency).
        variation_id: Variation primary key.

    Raises:
        HTTPException 404: If the variation does not exist.
    """
    deleted = await delete_variation(variation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Variation {variation_id} not found")

    logger.info("Deleted variation id=%d from product id=%d", variation_id, product_id)
    return ApiResponse(message="Variation deleted successfully")
