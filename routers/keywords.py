"""
Keywords Router – API Endpoints for crawling, researching, caching and applying keywords.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from database import (
    get_all_keyword_researches,
    get_keyword_research,
    get_product,
    update_product,
)
from models import ApiResponse, KeywordResearchRequest, KeywordResearchResponse
from modules.keyword_research import scrape_keywords, get_autocomplete_suggestions

logger = logging.getLogger("listing_helper.routers.keywords")
router = APIRouter()


@router.post("/research", response_model=ApiResponse)
async def keyword_research(body: KeywordResearchRequest):
    """Run keyword suggestion mining and organic search crawler.

    Args:
        body: Seed keywords, limit count, optional category, target marketplace, product_id, force_refresh.

    Returns:
        Categorised keyword lists.
    """
    if not body.seed_keywords:
        raise HTTPException(status_code=400, detail="At least one seed keyword is required")
    
    seed = body.seed_keywords[0].lower().strip()
    logger.info("Keyword research requested for: '%s' (limit=%d, product_id=%s, force_refresh=%s)", 
                seed, body.limit, body.product_id, body.force_refresh)

    try:
        # Check if already cached in DB to avoid unnecessary crawling unless force_refresh is True
        if not body.force_refresh:
            cached = await get_keyword_research(seed, product_id=body.product_id)
            if cached:
                logger.info("Found cached keyword research for: '%s'", seed)
                return ApiResponse(
                    message="Retrieved keyword research from cache",
                    data=cached["results"],
                )

        # Scrape using dual strategy & process NLP
        results = await scrape_keywords(seed, limit=body.limit, product_id=body.product_id)
        return ApiResponse(
            message="Keyword research completed successfully",
            data=results,
        )
    except Exception as exc:
        logger.exception("Failed to complete keyword research")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/research/stream")
async def keyword_research_stream(
    seed: str = Query(..., description="Seed keyword or Amazon URL"),
    limit: int = Query(50, ge=10, le=100),
    product_id: Optional[str] = Query(None),
    force_refresh: bool = Query(False),
):
    """Run keyword suggestion mining and organic search crawler, streaming progress back via SSE."""
    logger.info("Keyword research stream requested for: '%s' (limit=%d, product_id=%s, force_refresh=%s)", 
                seed, limit, product_id, force_refresh)
    
    parsed_product_id: Optional[int] = None
    if product_id and product_id.strip():
        try:
            parsed_product_id = int(product_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid product_id format")

    seed_clean = seed.lower().strip()
    
    # If not force_refresh, check cache first
    if not force_refresh:
        cached = await get_keyword_research(seed_clean, product_id=parsed_product_id)
        if cached:
            logger.info("Found cached keyword research for: '%s', returning cached event stream", seed_clean)
            async def cached_event_generator():
                # Yield starting links
                yield f"data: {json.dumps({'step': 'collecting_links', 'current': 0, 'total': 0, 'message': 'Loading from cache...'})}\n\n"
                await asyncio.sleep(0.1)
                # Yield complete
                yield f"data: {json.dumps({'step': 'complete', 'current': cached['results'].get('scraped_count', 0), 'total': cached['results'].get('total_links', 0), 'message': 'Loaded cached results successfully.', 'results': cached['results']})}\n\n"
            return StreamingResponse(cached_event_generator(), media_type="text/event-stream")

    queue = asyncio.Queue()

    async def progress_callback(data: dict[str, Any]):
        await queue.put(data)

    async def run_scraper():
        try:
            res = await scrape_keywords(
                seed=seed,
                limit=limit,
                product_id=parsed_product_id,
                progress_callback=progress_callback
            )
            # Add final results to the complete message so client gets it immediately
            await queue.put({
                "step": "complete",
                "current": res.get("scraped_count", 0),
                "total": res.get("total_links", 0),
                "message": f"Keyword research complete! Scraped {res.get('scraped_count', 0)} products.",
                "results": res
            })
        except Exception as exc:
            logger.exception("Scraper failed")
            await queue.put({"step": "error", "message": str(exc)})
        finally:
            await queue.put(None)

    asyncio.create_task(run_scraper())

    async def event_generator():
        while True:
            data = await queue.get()
            if data is None:
                break
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/autocomplete", response_model=ApiResponse)
async def autocomplete_suggestions(q: str = Query(..., description="Query prefix for suggestions")):
    """Get Amazon autocomplete suggestions for the query prefix."""
    try:
        suggestions = await get_autocomplete_suggestions(q)
        return ApiResponse(
            message="Fetched suggestions successfully",
            data=suggestions,
        )
    except Exception as exc:
        logger.exception("Autocomplete suggestions failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history", response_model=ApiResponse)
async def list_research_history(limit: int = Query(50, ge=1, le=100)):
    """Retrieve lists of previously searched seed keywords and their outcomes.

    Args:
        limit: Max past records to return.
    """
    try:
        history = await get_all_keyword_researches(limit=limit)
        # Format for overview lists
        formatted = []
        for h in history:
            formatted.append({
                "id": h["id"],
                "seed_keyword": h["seed_keyword"],
                "created_at": h["created_at"],
                "results_preview": {
                    "primary_count": len(h["results"].get("primary", [])),
                    "secondary_count": len(h["results"].get("secondary", [])),
                    "long_tail_count": len(h["results"].get("long_tail", [])),
                }
            })
        return ApiResponse(
            message="Research history loaded successfully",
            data=formatted,
        )
    except Exception as exc:
        logger.exception("Failed to load keyword history")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cached/{seed}", response_model=ApiResponse)
async def get_cached_research(seed: str):
    """Retrieve detailed research breakdown for a previously crawled seed.

    Args:
        seed: Seed keyword to fetch.
    """
    try:
        cached = await get_keyword_research(seed.lower().strip())
        if not cached:
            raise HTTPException(status_code=404, detail=f"No cached research found for seed '{seed}'")
        return ApiResponse(
            message="Cached research retrieved",
            data=cached["results"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to load cached research")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/apply-to-product", response_model=ApiResponse)
async def apply_keywords_to_product(
    product_id: int = Query(..., description="ID of product to apply to"),
    keywords: list[str] = Query(..., description="List of keywords to apply"),
):
    """Associate curated list of discovered keywords directly to a product draft.

    These keywords will be loaded into the LLM context when generating product listings.
    """
    existing = await get_product(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")

    try:
        # Update product's keywords_data field
        update_data = {
            "keywords_data": {
                "applied_keywords": keywords
            }
        }
        await update_product(product_id, update_data)
        logger.info("Applied %d keywords to product id=%d", len(keywords), product_id)
        return ApiResponse(
            message=f"Successfully applied {len(keywords)} keywords to product draft",
            data={"product_id": product_id, "applied_keywords": keywords}
        )
    except Exception as exc:
        logger.exception("Failed to apply keywords to product")
        raise HTTPException(status_code=500, detail=str(exc))
