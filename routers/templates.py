"""
Templates Router – Export marketplace listing templates and preview data.

Handles generating styled Excel workbooks via the ``excel_exporter``
module, serving previously generated files, listing export history,
and returning JSON preview data for the frontend UI.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import settings
from database import (
    create_export_record,
    get_all_variation_content_for_product,
    get_export_history,
    get_product,
    get_variations,
)
from models import ApiResponse, ExportHistoryResponse
from modules.excel_exporter import generate_export_excel

logger = logging.getLogger("listing_helper.routers.templates")
router = APIRouter()


# ============================================================================
# Request Models (local to this router)
# ============================================================================

class FullExportRequest(BaseModel):
    """Request body for preview and export endpoints.

    Accepts a list of product IDs and an optional marketplace filter
    (``all``, ``amazon``, ``flipkart``, or ``meesho``).
    """

    product_ids: list[int] = Field(..., min_length=1)
    marketplace: str = Field("all", pattern="^(all|amazon|flipkart|meesho)$")


# ============================================================================
# Helpers
# ============================================================================

async def _load_products_and_variations(
    product_ids: list[int],
) -> tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    """Load products and their variation content from the database.

    Args:
        product_ids: List of product primary keys.

    Returns:
        Tuple of (list of product dicts, variations_map).

    Raises:
        HTTPException 404: If any product ID is not found.
    """
    products: list[dict[str, Any]] = []
    variations_map: dict[int, list[dict[str, Any]]] = {}

    for pid in product_ids:
        product = await get_product(pid)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with ID {pid} not found",
            )
        products.append(product)
        variations_map[pid] = await get_all_variation_content_for_product(pid)

    return products, variations_map


def _build_preview_rows(
    products: list[dict[str, Any]],
    variations_map: dict[int, list[dict[str, Any]]],
    marketplace: str,
) -> list[dict[str, Any]]:
    """Build JSON-serialisable row dicts for UI preview.

    Each row is a flat dict representing what would be a spreadsheet
    row. Variation rows are included beneath their parent.

    Args:
        products: Product dicts.
        variations_map: product_id → variation content list.
        marketplace: ``all``, ``amazon``, ``flipkart``, or ``meesho``.

    Returns:
        List of row dicts.
    """
    rows: list[dict[str, Any]] = []

    for product in products:
        row = _product_to_preview_row(product, marketplace)
        rows.append(row)

        pid = product.get("id")
        for vc in variations_map.get(pid, []):
            # For marketplace-specific preview, only include matching variations
            if marketplace != "all" and vc.get("marketplace") != marketplace:
                continue
            var_row = _variation_to_preview_row(product, vc, marketplace)
            rows.append(var_row)

    return rows


def _product_to_preview_row(
    product: dict[str, Any],
    marketplace: str,
) -> dict[str, Any]:
    """Convert a product dict to a flat preview row."""
    base: dict[str, Any] = {
        "sku": product.get("sku"),
        "name": product.get("name"),
        "brand": product.get("brand"),
        "category": product.get("category"),
        "cost_price": product.get("cost_price"),
        "weight_grams": product.get("weight_grams"),
        "listing_status": product.get("listing_status", "new"),
        "is_variation": False,
    }

    if marketplace in ("all", "amazon"):
        base["amazon_title"] = product.get("amazon_title")
        base["amazon_description"] = product.get("amazon_description")
        base["amazon_search_terms"] = product.get("amazon_search_terms")
        base["amazon_price"] = product.get("amazon_price")
        bullets = product.get("amazon_bullets") or []
        if isinstance(bullets, list):
            for i, b in enumerate(bullets[:5], start=1):
                base[f"amazon_bullet_{i}"] = b

    if marketplace in ("all", "flipkart"):
        base["flipkart_title"] = product.get("flipkart_title")
        base["flipkart_description"] = product.get("flipkart_description")
        base["flipkart_keywords"] = product.get("flipkart_search_keywords")
        base["flipkart_price"] = product.get("flipkart_price")
        features = product.get("flipkart_key_features") or []
        if isinstance(features, list):
            for i, f in enumerate(features[:6], start=1):
                base[f"flipkart_key_feature_{i}"] = f

    if marketplace in ("all", "meesho"):
        base["meesho_title"] = product.get("meesho_title")
        base["meesho_description"] = product.get("meesho_description")
        base["meesho_price"] = product.get("meesho_price")

    return base


def _variation_to_preview_row(
    parent: dict[str, Any],
    vc: dict[str, Any],
    marketplace: str,
) -> dict[str, Any]:
    """Convert a variation content dict to a flat preview row."""
    var_mp = vc.get("marketplace", "")
    var_label = f"{vc.get('variation_type', '')}: {vc.get('variation_value', '')}"

    row: dict[str, Any] = {
        "sku": vc.get("variation_sku") or vc.get("sku") or parent.get("sku"),
        "name": f"{parent.get('name', '')} ({var_label})",
        "brand": parent.get("brand"),
        "category": parent.get("category"),
        "cost_price": parent.get("cost_price"),
        "weight_grams": parent.get("weight_grams"),
        "listing_status": parent.get("listing_status", "new"),
        "is_variation": True,
        "variation_type": vc.get("variation_type"),
        "variation_value": vc.get("variation_value"),
    }

    # Fill marketplace-specific columns from variation content
    if marketplace in ("all", "amazon"):
        if var_mp == "amazon":
            row["amazon_title"] = vc.get("title")
            row["amazon_description"] = vc.get("description")
            row["amazon_search_terms"] = vc.get("keywords")
        else:
            row["amazon_title"] = parent.get("amazon_title")
            row["amazon_description"] = parent.get("amazon_description")
            row["amazon_search_terms"] = parent.get("amazon_search_terms")
        row["amazon_price"] = parent.get("amazon_price")

    if marketplace in ("all", "flipkart"):
        if var_mp == "flipkart":
            row["flipkart_title"] = vc.get("title")
            row["flipkart_description"] = vc.get("description")
            row["flipkart_keywords"] = vc.get("keywords")
        else:
            row["flipkart_title"] = parent.get("flipkart_title")
            row["flipkart_description"] = parent.get("flipkart_description")
            row["flipkart_keywords"] = parent.get("flipkart_search_keywords")
        row["flipkart_price"] = parent.get("flipkart_price")

    if marketplace in ("all", "meesho"):
        if var_mp == "meesho":
            row["meesho_title"] = vc.get("title")
            row["meesho_description"] = vc.get("description")
        else:
            row["meesho_title"] = parent.get("meesho_title")
            row["meesho_description"] = parent.get("meesho_description")
        row["meesho_price"] = parent.get("meesho_price")

    return row


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/preview", response_model=ApiResponse)
async def preview_export(body: FullExportRequest):
    """Return JSON data structured as a table for UI rendering.

    This returns the same data that would go into an Excel export,
    but as a list of row dicts for frontend preview.

    Args:
        body: Product IDs and optional marketplace filter.

    Returns:
        ApiResponse with a list of row dicts in ``data``.
    """
    logger.info(
        "Preview requested: marketplace=%s, product_ids=%s",
        body.marketplace,
        body.product_ids,
    )

    products, variations_map = await _load_products_and_variations(body.product_ids)
    rows = _build_preview_rows(products, variations_map, body.marketplace)

    return ApiResponse(
        message=f"Preview generated for {len(products)} products ({len(rows)} total rows)",
        data=rows,
    )


@router.post("/export", response_model=None)
async def export_template(body: FullExportRequest):
    """Generate and return an actual Excel file for download.

    Uses ``generate_export_excel`` to create a styled ``.xlsx``
    workbook. The export is recorded in the ``export_history`` table.

    Args:
        body: Product IDs and optional marketplace filter.

    Returns:
        FileResponse with the generated Excel file.
    """
    logger.info(
        "Export requested: marketplace=%s, product_ids=%s",
        body.marketplace,
        body.product_ids,
    )

    products, variations_map = await _load_products_and_variations(body.product_ids)

    # Generate Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{body.marketplace}_listing_export_{timestamp}.xlsx"

    try:
        file_path = generate_export_excel(
            products=products,
            variations_map=variations_map,
            filename=filename,
        )
    except Exception as exc:
        logger.exception("Excel generation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Excel generation failed: {exc}",
        )

    # Record in export history
    for pid in body.product_ids:
        await create_export_record({
            "product_id": pid,
            "marketplace": body.marketplace,
            "file_path": file_path,
            "export_type": "template",
            "status": "completed",
        })

    logger.info("Export complete: %s (%d products)", file_path, len(products))

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/exports", response_model=ApiResponse)
async def list_exports():
    """List recent export history.

    Returns the 50 most recent export records ordered by date
    descending.
    """
    history = await get_export_history(limit=50)
    return ApiResponse(
        data=[ExportHistoryResponse(**h).model_dump() for h in history],
    )


@router.get("/download/{filename:path}")
async def download_export(filename: str):
    """Serve a previously generated export file.

    Looks up the file in the configured ``EXPORT_PATH`` directory
    and returns it as a download.

    Args:
        filename: Name of the export file.

    Returns:
        FileResponse with the requested file.

    Raises:
        HTTPException 404: If the file does not exist.
    """
    export_dir = Path(settings.EXPORT_PATH)
    file_path = export_dir / filename

    # Security: prevent directory traversal
    try:
        file_path = file_path.resolve()
        export_dir_resolved = export_dir.resolve()
        if not str(file_path).startswith(str(export_dir_resolved)):
            raise HTTPException(status_code=400, detail="Invalid filename")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Export file '{filename}' not found",
        )

    logger.info("Serving export file: %s", file_path)

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{file_path.name}"',
        },
    )
