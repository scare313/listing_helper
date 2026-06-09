"""
Pydantic models for Listing Helper.

Defines request/response schemas for the API including products,
marketplace content, keyword research, pricing calculations, and exports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Generic API Response Wrapper
# ============================================================================

class ApiResponse(BaseModel):
    """Standard wrapper returned by every endpoint."""

    success: bool = True
    message: str = "OK"
    data: Any = None


# ============================================================================
# Product Models
# ============================================================================

class ProductBase(BaseModel):
    """Shared product fields used for creation and display."""

    name: str = Field(..., min_length=1, max_length=500, description="Product name")
    brand: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=200)
    subcategory: Optional[str] = Field(None, max_length=200)
    cost_price: Optional[float] = Field(None, ge=0, description="Cost price in ₹")
    weight_grams: Optional[float] = Field(None, ge=0)
    length_cm: Optional[float] = Field(None, ge=0)
    width_cm: Optional[float] = Field(None, ge=0)
    height_cm: Optional[float] = Field(None, ge=0)
    hsn_code: Optional[str] = Field(None, max_length=20)
    gst_rate: float = Field(18.0, ge=0, le=100)
    notes: Optional[str] = None


class ProductCreate(ProductBase):
    """Schema for creating a new product."""

    sku: str = Field(..., min_length=1, max_length=100, description="Unique SKU")


class ProductUpdate(BaseModel):
    """Schema for partial product updates – every field is optional."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=500)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    cost_price: Optional[float] = Field(None, ge=0)
    weight_grams: Optional[float] = Field(None, ge=0)
    length_cm: Optional[float] = Field(None, ge=0)
    width_cm: Optional[float] = Field(None, ge=0)
    height_cm: Optional[float] = Field(None, ge=0)
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None

    # Amazon fields
    amazon_title: Optional[str] = None
    amazon_bullets: Optional[list[str]] = None
    amazon_description: Optional[str] = None
    amazon_search_terms: Optional[str] = None
    amazon_asin: Optional[str] = None
    amazon_status: Optional[str] = None
    amazon_price: Optional[float] = Field(None, ge=0)

    # Flipkart fields
    flipkart_title: Optional[str] = None
    flipkart_key_features: Optional[list[str]] = None
    flipkart_description: Optional[str] = None
    flipkart_search_keywords: Optional[str] = None
    flipkart_fsn: Optional[str] = None
    flipkart_status: Optional[str] = None
    flipkart_price: Optional[float] = Field(None, ge=0)

    # Meesho fields
    meesho_title: Optional[str] = None
    meesho_description: Optional[str] = None
    meesho_group_id: Optional[str] = None
    meesho_product_id: Optional[str] = None
    meesho_status: Optional[str] = None
    meesho_price: Optional[float] = Field(None, ge=0)

    # Structured data
    keywords_data: Optional[dict[str, Any]] = None
    competitor_data: Optional[dict[str, Any]] = None

    # Workflow tracking (v2.0)
    listing_status: Optional[str] = None


class ProductResponse(ProductBase):
    """Full product representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str

    # Amazon
    amazon_title: Optional[str] = None
    amazon_bullets: Optional[list[str]] = None
    amazon_description: Optional[str] = None
    amazon_search_terms: Optional[str] = None
    amazon_asin: Optional[str] = None
    amazon_status: str = "draft"
    amazon_price: Optional[float] = None

    # Flipkart
    flipkart_title: Optional[str] = None
    flipkart_key_features: Optional[list[str]] = None
    flipkart_description: Optional[str] = None
    flipkart_search_keywords: Optional[str] = None
    flipkart_fsn: Optional[str] = None
    flipkart_status: str = "draft"
    flipkart_price: Optional[float] = None

    # Meesho
    meesho_title: Optional[str] = None
    meesho_description: Optional[str] = None
    meesho_group_id: Optional[str] = None
    meesho_product_id: Optional[str] = None
    meesho_status: str = "draft"
    meesho_price: Optional[float] = None

    # Meta
    keywords_data: Optional[dict[str, Any]] = None
    competitor_data: Optional[dict[str, Any]] = None
    listing_status: str = "new"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProductListResponse(BaseModel):
    """Paginated list of products."""

    products: list[ProductResponse]
    total: int
    page: int
    per_page: int


# ============================================================================
# Variation Models
# ============================================================================

class VariationCreate(BaseModel):
    """Schema for adding a product variation."""

    variation_type: str = Field(..., description="e.g. 'color', 'size'")
    variation_value: str = Field(..., description="e.g. 'Red', 'L'")
    sku: str = Field(..., min_length=1, max_length=100)
    additional_cost: float = Field(0.0, ge=0)
    stock_quantity: int = Field(0, ge=0)


class VariationResponse(VariationCreate):
    """Variation with database identifiers."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: Optional[str] = None


# ============================================================================
# Marketplace Content Models
# ============================================================================

class MarketplaceContent(BaseModel):
    """Generated listing content for a single marketplace."""

    title: str = ""
    bullets: Optional[list[str]] = None       # Amazon bullet points
    key_features: Optional[list[str]] = None  # Flipkart key features
    description: str = ""
    keywords: Optional[str] = None
    search_terms: Optional[str] = None


class ContentGenerationRequest(BaseModel):
    """Request body for AI content generation."""

    product_id: Optional[int] = None
    marketplace: str = Field(..., pattern="^(amazon|flipkart|meesho|all)$")
    keywords: list[str] = Field(default_factory=list)
    product_details: Optional[dict[str, Any]] = None


class ContentGenerationResponse(BaseModel):
    """Generated content for one or more marketplaces."""

    amazon: Optional[MarketplaceContent] = None
    flipkart: Optional[MarketplaceContent] = None
    meesho: Optional[MarketplaceContent] = None


# ============================================================================
# Keyword Research Models
# ============================================================================

class KeywordResearchRequest(BaseModel):
    """Request body for keyword research."""

    seed_keywords: list[str] = Field(..., min_length=1)
    category: Optional[str] = None
    marketplace: str = Field("amazon", pattern="^(amazon|flipkart|meesho|all)$")
    limit: int = Field(50, ge=10, le=100)
    product_id: Optional[int] = None
    force_refresh: bool = False


class KeywordResearchResponse(BaseModel):
    """Structured keyword research results."""

    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)
    long_tail: list[str] = Field(default_factory=list)
    trending: list[str] = Field(default_factory=list)
    autocomplete: list[str] = Field(default_factory=list)


# ============================================================================
# Pricing Models
# ============================================================================

class PricingRequest(BaseModel):
    """Request body for pricing calculation."""

    product_id: Optional[int] = None
    cost_price: float = Field(..., ge=0)
    weight_grams: float = Field(..., ge=0)
    length_cm: float = Field(0, ge=0)
    width_cm: float = Field(0, ge=0)
    height_cm: float = Field(0, ge=0)
    category: str = ""
    target_margin: float = Field(25.0, ge=0, le=100)
    shipping_zone: str = Field("national", pattern="^(local|regional|zonal|national)$")


class MarketplacePricing(BaseModel):
    """Per-marketplace pricing breakdown."""

    selling_price: float = 0
    fees: dict[str, float] = Field(default_factory=dict)
    total_fees: float = 0
    profit: float = 0
    margin_percent: float = 0


class PricingResponse(BaseModel):
    """Pricing calculations for all marketplaces."""

    amazon: Optional[MarketplacePricing] = None
    flipkart: Optional[MarketplacePricing] = None
    meesho: Optional[MarketplacePricing] = None


# ============================================================================
# Export Models
# ============================================================================

class ExportRequest(BaseModel):
    """Request body for template export."""

    product_ids: list[int] = Field(..., min_length=1)
    marketplace: str = Field("all", pattern="^(amazon|flipkart|meesho|all)$")


class ExportResponse(BaseModel):
    """Result of an export operation."""

    file_path: str
    filename: str = ""
    products_exported: int


class ExportHistoryResponse(BaseModel):
    """Single row from export_history table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: Optional[int] = None
    marketplace: str
    file_path: str
    export_type: Optional[str] = None
    status: str = "completed"
    created_at: Optional[str] = None


# ============================================================================
# Vision Detection Models (v2.0)
# ============================================================================

class VisionDetectionResponse(BaseModel):
    """Product attributes detected from an image."""

    product_type: Optional[str] = None
    suggested_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    material: Optional[str] = None
    colors: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)
    suggested_keywords: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None


# ============================================================================
# Content Validation Models (v2.0)
# ============================================================================

class ContentValidationItem(BaseModel):
    """Single field validation result."""

    field: str
    marketplace: str
    length: int
    limit: int
    is_valid: bool
    message: str = ""


class ContentValidationRequest(BaseModel):
    """Request body for content validation."""

    marketplace: str = Field(..., pattern="^(amazon|flipkart|meesho)$")
    title: str = ""
    bullets: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)
    description: str = ""
    keywords: str = ""
    search_terms: str = ""


# ============================================================================
# Variation Content Models (v2.0)
# ============================================================================

class VariationContentResponse(BaseModel):
    """Content for a specific product variation on a marketplace."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    variation_id: int
    marketplace: str
    title: Optional[str] = None
    bullets: Optional[list[str]] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    status: str = "draft"
    created_at: Optional[str] = None
    # Joined fields from product_variations
    variation_type: Optional[str] = None
    variation_value: Optional[str] = None
    variation_sku: Optional[str] = None


class ContentWithVariationsRequest(BaseModel):
    """Request body for content generation with variations."""

    product_id: int
    keywords: list[str] = Field(default_factory=list)
    marketplace: str = Field("all", pattern="^(amazon|flipkart|meesho|all)$")


class ExportPreviewRequest(BaseModel):
    """Request body for export preview."""

    product_ids: list[int] = Field(..., min_length=1)
    marketplace: str = Field("all", pattern="^(amazon|flipkart|meesho|all)$")
