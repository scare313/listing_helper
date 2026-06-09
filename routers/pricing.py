"""
Pricing Router – Fee calculation and margin analysis (stub).

Calculates selling prices, marketplace fees, profits, and margins
for Amazon India, Flipkart, and Meesho.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from config import (
    AMAZON_FEES,
    FLIPKART_FEES,
    MEESHO_FEES,
    get_closing_fee,
    get_referral_fee_rate,
    get_shipping_fee,
)
from models import (
    ApiResponse,
    MarketplacePricing,
    PricingRequest,
    PricingResponse,
)
from database import get_product, save_pricing_snapshot, update_product

logger = logging.getLogger("listing_helper.routers.pricing")
router = APIRouter()


def _calculate_marketplace_pricing(
    marketplace: str,
    cost_price: float,
    selling_price: float,
    weight_grams: float,
    category_key: str,
    shipping_zone: str,
    gst_rate: float = 18.0,
) -> MarketplacePricing:
    """Calculate fees, profit, and margin for a single marketplace.

    Args:
        marketplace: ``amazon``, ``flipkart``, or ``meesho``.
        cost_price: Product cost price in ₹.
        selling_price: Target selling price in ₹.
        weight_grams: Product weight in grams.
        category_key: Internal category key for fee lookup.
        shipping_zone: ``local``, ``regional``/``zonal``, or ``national``.
        gst_rate: GST percentage (default 18%).

    Returns:
        Detailed pricing breakdown.
    """
    referral_rate = get_referral_fee_rate(marketplace, category_key, selling_price)
    referral_fee = round(selling_price * referral_rate, 2)

    closing_fee = get_closing_fee(marketplace, selling_price)
    shipping_fee = get_shipping_fee(marketplace, weight_grams, shipping_zone)

    # Collection fee (Flipkart only)
    collection_fee = 0.0
    if marketplace == "flipkart":
        coll = FLIPKART_FEES["collection_fees"]
        collection_fee = max(
            coll["min"],
            min(selling_price * coll["percentage"], coll["max"]),
        )

    # GST on marketplace fees
    marketplace_fees_subtotal = referral_fee + closing_fee + shipping_fee + collection_fee
    gst_on_mp_fees_rate = {
        "amazon": AMAZON_FEES["gst_on_fees"],
        "flipkart": FLIPKART_FEES["gst_on_fees"],
        "meesho": MEESHO_FEES.get("gst_on_shipping", 0.18),
    }.get(marketplace, 0.18)
    gst_on_fees = round(marketplace_fees_subtotal * gst_on_mp_fees_rate, 2)

    total_fees = round(marketplace_fees_subtotal + gst_on_fees, 2)
    profit = round(selling_price - cost_price - total_fees, 2)
    margin_percent = round((profit / selling_price) * 100, 2) if selling_price > 0 else 0

    fees_dict = {
        "referral_fee": referral_fee,
        "closing_fee": closing_fee,
        "shipping_fee": shipping_fee,
        "gst_on_fees": gst_on_fees,
    }
    if marketplace == "flipkart":
        fees_dict["collection_fee"] = collection_fee

    return MarketplacePricing(
        selling_price=selling_price,
        fees=fees_dict,
        total_fees=total_fees,
        profit=profit,
        margin_percent=margin_percent,
    )


def _calculate_target_price(
    marketplace: str,
    cost_price: float,
    target_margin: float,
    weight_grams: float,
    category_key: str,
    shipping_zone: str,
) -> float:
    """Reverse-calculate the selling price needed to achieve a target margin.

    Uses iterative approximation since fees depend on the selling price.

    Args:
        marketplace: Marketplace name.
        cost_price: Cost price in ₹.
        target_margin: Desired margin percentage.
        weight_grams: Product weight in grams.
        category_key: Category key for fee lookup.
        shipping_zone: Shipping zone.

    Returns:
        Estimated selling price in ₹.
    """
    # Start with a rough estimate
    price = cost_price / (1 - target_margin / 100) * 1.3
    for _ in range(20):  # converge in ~10 iterations
        result = _calculate_marketplace_pricing(
            marketplace, cost_price, price, weight_grams, category_key, shipping_zone,
        )
        if abs(result.margin_percent - target_margin) < 0.1:
            break
        # Adjust price
        needed_profit = price * target_margin / 100
        actual_profit = result.profit
        price += (needed_profit - actual_profit) * 0.8

    return round(max(price, cost_price), 2)


@router.post("/calculate", response_model=ApiResponse)
async def calculate_pricing(body: PricingRequest):
    """Calculate pricing for all marketplaces.

    **Stub-enhanced implementation** – uses the fee structure constants
    from config to produce realistic calculations.

    For each marketplace, the endpoint reverse-calculates the selling
    price needed to hit the target margin, then returns a detailed
    fee breakdown.

    Args:
        body: Cost price, weight, dimensions, category, and target margin.

    Returns:
        Per-marketplace pricing breakdown.
    """
    logger.info(
        "Pricing calculation: cost=%.2f, weight=%.0fg, margin=%.1f%%",
        body.cost_price,
        body.weight_grams,
        body.target_margin,
    )

    category_key = body.category or "default"
    results: dict[str, MarketplacePricing] = {}

    for mp in ("amazon", "flipkart", "meesho"):
        target_price = _calculate_target_price(
            mp, body.cost_price, body.target_margin,
            body.weight_grams, category_key, body.shipping_zone,
        )
        results[mp] = _calculate_marketplace_pricing(
            mp, body.cost_price, target_price,
            body.weight_grams, category_key, body.shipping_zone,
        )

    response = PricingResponse(
        amazon=results["amazon"],
        flipkart=results["flipkart"],
        meesho=results["meesho"],
    )

    # Save snapshot and update product prices if product_id is provided
    if body.product_id:
        try:
            for mp in ("amazon", "flipkart", "meesho"):
                res_mp = results[mp]
                await save_pricing_snapshot({
                    "product_id": body.product_id,
                    "marketplace": mp,
                    "selling_price": res_mp.selling_price,
                    "fees_breakdown": res_mp.fees,
                    "profit": res_mp.profit,
                    "margin_percent": res_mp.margin_percent,
                })
            
            await update_product(body.product_id, {
                "amazon_price": results["amazon"].selling_price,
                "flipkart_price": results["flipkart"].selling_price,
                "meesho_price": results["meesho"].selling_price,
                "listing_status": "priced"
            })
            logger.info("Saved pricing snapshots and updated product prices for product_id=%d", body.product_id)
        except Exception as exc:
            logger.exception("Failed to save pricing snapshots or update product prices")
            raise HTTPException(status_code=500, detail=f"Failed to save pricing results: {exc}")

    return ApiResponse(
        message="Pricing calculated successfully",
        data=response.model_dump(),
    )


@router.post("/calculate/batch", response_model=ApiResponse)
async def calculate_batch_pricing(bodies: list[PricingRequest]):
    """Calculate pricing for multiple products at once.

    **Stub implementation** – iterates through each request and
    returns a list of pricing responses.

    Args:
        bodies: List of pricing requests.

    Returns:
        List of per-product pricing breakdowns.
    """
    logger.info("Batch pricing requested for %d products", len(bodies))

    all_results = []
    for body in bodies:
        category_key = body.category or "default"
        results: dict[str, MarketplacePricing] = {}

        for mp in ("amazon", "flipkart", "meesho"):
            target_price = _calculate_target_price(
                mp, body.cost_price, body.target_margin,
                body.weight_grams, category_key, body.shipping_zone,
            )
            results[mp] = _calculate_marketplace_pricing(
                mp, body.cost_price, target_price,
                body.weight_grams, category_key, body.shipping_zone,
            )

        all_results.append(PricingResponse(
            amazon=results["amazon"],
            flipkart=results["flipkart"],
            meesho=results["meesho"],
        ).model_dump())

    return ApiResponse(
        message=f"Batch pricing calculated for {len(bodies)} products",
        data=all_results,
    )


@router.post("/auto-price/{product_id}", response_model=ApiResponse)
async def auto_price_product(
    product_id: int,
    target_margin: float = Query(25.0, ge=0, le=100),
    shipping_zone: str = Query("national", pattern="^(local|regional|zonal|national)$"),
):
    """Auto-price a product by reading its cost and weight from the DB.

    Reads ``cost_price``, ``weight_grams``, and ``category`` from the stored
    product record, then reverse-calculates the selling price needed to hit
    ``target_margin`` for each marketplace and persists the results.

    Args:
        product_id: Primary key of the product to price.
        target_margin: Desired margin percentage (default 25%).
        shipping_zone: Shipping zone used for fee lookup (default ``national``).

    Returns:
        Per-marketplace pricing breakdown.

    Raises:
        HTTPException 404: If the product does not exist.
        HTTPException 400: If the product has no cost price set.
    """
    product = await get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

    cost_price = product.get("cost_price")
    if not cost_price:
        raise HTTPException(
            status_code=400,
            detail="Product has no cost price set. Update the product before auto-pricing.",
        )

    weight_grams = product.get("weight_grams") or 500.0
    category_key = product.get("category") or "default"

    logger.info(
        "Auto-pricing product_id=%d cost=%.2f weight=%.0fg margin=%.1f%%",
        product_id, cost_price, weight_grams, target_margin,
    )

    results: dict[str, MarketplacePricing] = {}
    for mp in ("amazon", "flipkart", "meesho"):
        target_price = _calculate_target_price(
            mp, cost_price, target_margin, weight_grams, category_key, shipping_zone,
        )
        results[mp] = _calculate_marketplace_pricing(
            mp, cost_price, target_price, weight_grams, category_key, shipping_zone,
        )

    try:
        for mp in ("amazon", "flipkart", "meesho"):
            res_mp = results[mp]
            await save_pricing_snapshot({
                "product_id": product_id,
                "marketplace": mp,
                "selling_price": res_mp.selling_price,
                "fees_breakdown": res_mp.fees,
                "profit": res_mp.profit,
                "margin_percent": res_mp.margin_percent,
            })

        await update_product(product_id, {
            "amazon_price": results["amazon"].selling_price,
            "flipkart_price": results["flipkart"].selling_price,
            "meesho_price": results["meesho"].selling_price,
            "listing_status": "priced",
        })
        logger.info("Auto-price complete for product_id=%d", product_id)
    except Exception as exc:
        logger.exception("Failed to save auto-price results for product_id=%d", product_id)
        raise HTTPException(status_code=500, detail=f"Failed to save pricing results: {exc}")

    response = PricingResponse(
        amazon=results["amazon"],
        flipkart=results["flipkart"],
        meesho=results["meesho"],
    )
    return ApiResponse(
        message=f"Product {product_id} auto-priced successfully",
        data=response.model_dump(),
    )


@router.get("/fee-structure/{marketplace}", response_model=ApiResponse)
async def get_fee_structure(marketplace: str):
    """Return the full fee structure constants for a marketplace.

    Args:
        marketplace: One of ``amazon``, ``flipkart``, or ``meesho``.

    Raises:
        HTTPException 404: If the marketplace is not recognised.

    Returns:
        Complete fee structure dictionary.
    """
    fee_map = {
        "amazon": AMAZON_FEES,
        "flipkart": FLIPKART_FEES,
        "meesho": MEESHO_FEES,
    }

    if marketplace not in fee_map:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown marketplace: '{marketplace}'. Must be one of: amazon, flipkart, meesho",
        )

    return ApiResponse(
        data={"marketplace": marketplace, "fee_structure": fee_map[marketplace]},
    )
