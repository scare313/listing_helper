"""
Content Generator Module – AI-Powered Listing Optimization via Gemini API.

Ingests product details and applied keywords to generate highly optimized,
marketplace-compliant listing copy for Amazon, Flipkart, and Meesho.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from google import genai
from google.genai import types

from config import settings, MARKETPLACE_LIMITS
from database import get_setting
from models import ContentGenerationResponse, MarketplaceContent

logger = logging.getLogger("listing_helper.modules.content_generator")


# ============================================================================
# Prompt Builders – per-marketplace
# ============================================================================

def _format_product_specs(product_details: dict[str, Any]) -> str:
    """Format product specification block shared across all marketplace prompts.

    Args:
        product_details: Product dict from the database.

    Returns:
        Formatted multi-line string of product specifications.
    """
    name = product_details.get("name", "Product")
    brand = product_details.get("brand", "Generic")
    category = product_details.get("category", "General")
    material = product_details.get("material", "")
    notes = product_details.get("notes", "")

    # Build dimensions string from available fields
    dims_parts: list[str] = []
    for dim_key in ("length_cm", "width_cm", "height_cm"):
        val = product_details.get(dim_key)
        if val:
            dims_parts.append(f"{dim_key.replace('_cm', '').title()}: {val} cm")
    weight = product_details.get("weight_grams")
    if weight:
        dims_parts.append(f"Weight: {weight}g")
    dimensions_str = ", ".join(dims_parts) if dims_parts else "Not specified"

    return (
        f"- Name: {name}\n"
        f"- Brand: {brand}\n"
        f"- Category: {category}\n"
        f"- Material: {material or 'Not specified'}\n"
        f"- Dimensions: {dimensions_str}\n"
        f"- Special Notes: {notes or 'None'}"
    )


def _format_keywords(keywords: list[str]) -> str:
    """Format the top 15 keywords as a bullet list for prompt injection.

    Args:
        keywords: List of target keywords.

    Returns:
        Newline-separated bullet list of keywords.
    """
    return "\n".join(f"- {kw}" for kw in keywords[:15])


def _format_variation_instruction(variation_info: dict[str, str] | None) -> str:
    """Build a variation-specific instruction block for the prompt.

    Args:
        variation_info: Dict with 'variation_type' and 'variation_value', or None.

    Returns:
        Variation instruction string (empty if no variation).
    """
    if not variation_info:
        return ""

    v_type = variation_info.get("variation_type", "variant")
    v_value = variation_info.get("variation_value", "")
    return (
        f"\n\nVARIATION-SPECIFIC INSTRUCTIONS:\n"
        f"This listing is for a specific variant: {v_type} = '{v_value}'.\n"
        f"- Customize the title to naturally include '{v_value}' as the {v_type}.\n"
        f"- Adapt the first bullet point / key feature to highlight the '{v_value}' {v_type}.\n"
        f"- The rest of the content should remain product-accurate but may reference "
        f"the '{v_value}' variant where natural.\n"
    )


def _build_amazon_prompt(
    product_details: dict[str, Any],
    keywords: list[str],
    variation_info: dict[str, str] | None = None,
) -> str:
    """Build an Amazon India–specific content generation prompt.

    Incorporates exact character limits from MARKETPLACE_LIMITS and instructs
    the AI to produce JSON matching the MarketplaceContent schema.

    Args:
        product_details: Product specs dict.
        keywords: Curated target keywords (top 15 used).
        variation_info: Optional variation context for variant-specific content.

    Returns:
        Complete prompt string for Amazon content generation.
    """
    limits = MARKETPLACE_LIMITS["amazon"]
    specs = _format_product_specs(product_details)
    kw_block = _format_keywords(keywords)
    variation_block = _format_variation_instruction(variation_info)

    return f"""You are a senior e-commerce SEO copywriter specializing in Amazon India.
Generate a high-converting, keyword-rich product listing.

PRODUCT SPECIFICATIONS:
{specs}

TARGET KEYWORDS (inject these naturally – prioritize in title and bullets):
{kw_block}

AMAZON INDIA COMPLIANCE RULES:
- Title: Maximum {limits['title_max_chars']} characters. Format: Brand + Product Name + Main Keyword + Key Attributes. Aim for ~80 chars for mobile readability.
- Bullet Points: Exactly {limits['bullet_count']} bullets. Max {limits['bullet_max_chars']} characters each. Benefit-driven. Format: "BENEFIT HEADER – Explanation of feature."
- Description: Maximum {limits['description_max_chars']} characters. Engaging, story-based. Use double line breaks for paragraphs. No HTML bold tags.
- Search Terms: Maximum {limits['search_terms_max_bytes']} bytes. Lowercase, space-separated, no duplicate words, no commas, no brand names.
{variation_block}
Respond ONLY with a JSON object:
{{
    "title": "string",
    "bullets": ["bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
    "description": "string",
    "search_terms": "string"
}}"""


def _build_flipkart_prompt(
    product_details: dict[str, Any],
    keywords: list[str],
    variation_info: dict[str, str] | None = None,
) -> str:
    """Build a Flipkart-specific content generation prompt.

    Incorporates exact character limits from MARKETPLACE_LIMITS and instructs
    the AI to produce JSON matching the MarketplaceContent schema.

    Args:
        product_details: Product specs dict.
        keywords: Curated target keywords (top 15 used).
        variation_info: Optional variation context for variant-specific content.

    Returns:
        Complete prompt string for Flipkart content generation.
    """
    limits = MARKETPLACE_LIMITS["flipkart"]
    specs = _format_product_specs(product_details)
    kw_block = _format_keywords(keywords)
    variation_block = _format_variation_instruction(variation_info)

    return f"""You are a senior e-commerce SEO copywriter specializing in Flipkart India.
Generate a high-converting, keyword-rich product listing.

PRODUCT SPECIFICATIONS:
{specs}

TARGET KEYWORDS (inject these naturally – prioritize in title and features):
{kw_block}

FLIPKART COMPLIANCE RULES:
- Title: Maximum {limits['title_max_chars']} characters. Factual, keyword-focused.
- Key Features: {limits['key_features_count']} features max. Each max {limits['key_feature_max_chars']} characters. Focus on technical specs (materials, weight, sizes, durability).
- Description: Maximum {limits['description_max_chars']} characters. Bulleted, factual specs. Highlight value for money.
- Search Keywords: Maximum {limits['search_keywords_max_chars']} characters. 5 primary terms separated by double colons, e.g. "term1::term2::term3::term4::term5".
{variation_block}
Respond ONLY with a JSON object:
{{
    "title": "string",
    "key_features": ["feature 1", "feature 2", ...],
    "description": "string",
    "keywords": "string"
}}"""


def _build_meesho_prompt(
    product_details: dict[str, Any],
    keywords: list[str],
    variation_info: dict[str, str] | None = None,
) -> str:
    """Build a Meesho-specific content generation prompt.

    Incorporates exact character limits from MARKETPLACE_LIMITS and instructs
    the AI to produce JSON matching the MarketplaceContent schema.

    Args:
        product_details: Product specs dict.
        keywords: Curated target keywords (top 15 used).
        variation_info: Optional variation context for variant-specific content.

    Returns:
        Complete prompt string for Meesho content generation.
    """
    limits = MARKETPLACE_LIMITS["meesho"]
    specs = _format_product_specs(product_details)
    kw_block = _format_keywords(keywords)
    variation_block = _format_variation_instruction(variation_info)

    return f"""You are a senior e-commerce SEO copywriter specializing in Meesho India.
Generate a high-converting product listing optimized for Meesho's audience.

PRODUCT SPECIFICATIONS:
{specs}

TARGET KEYWORDS (embed ALL of these naturally in the description – Meesho has no backend keywords field):
{kw_block}

MEESHO COMPLIANCE RULES:
- Title: {limits['title_max_chars']} characters max. Simple language, price-value oriented. Highlight COD/Free Delivery appeal.
- Description: Maximum {limits['description_max_chars']} characters. Simple Hinglish/English accessible language. Include dimensions, care instructions, materials. Embed ALL keywords naturally since there is no separate keywords field.
{variation_block}
Respond ONLY with a JSON object:
{{
    "title": "string",
    "description": "string"
}}"""


# ============================================================================
# Content Validation
# ============================================================================

def validate_content(content: MarketplaceContent, marketplace: str) -> list[dict]:
    """Validate generated content against marketplace character limits.

    Checks each field of the content against the corresponding limit defined
    in ``MARKETPLACE_LIMITS``. Returns a detailed validation report per field.

    Args:
        content: A ``MarketplaceContent`` instance to validate.
        marketplace: Target marketplace (``amazon``, ``flipkart``, or ``meesho``).

    Returns:
        List of dicts, each with keys: ``field``, ``value`` (truncated preview),
        ``length``, ``limit``, ``is_valid``, and ``message``.
    """
    limits = MARKETPLACE_LIMITS.get(marketplace, {})
    results: list[dict] = []

    # --- Title ---
    title_limit = limits.get("title_max_chars", 500)
    title_len = len(content.title)
    results.append({
        "field": "title",
        "value": content.title[:80] + ("..." if title_len > 80 else ""),
        "length": title_len,
        "limit": title_limit,
        "is_valid": title_len <= title_limit,
        "message": (
            f"Title OK ({title_len}/{title_limit} chars)"
            if title_len <= title_limit
            else f"Title exceeds limit by {title_len - title_limit} chars ({title_len}/{title_limit})"
        ),
    })

    # --- Bullets (Amazon) ---
    if marketplace == "amazon" and content.bullets:
        bullet_limit = limits.get("bullet_max_chars", 500)
        for i, bullet in enumerate(content.bullets):
            b_len = len(bullet)
            results.append({
                "field": f"bullet_{i + 1}",
                "value": bullet[:80] + ("..." if b_len > 80 else ""),
                "length": b_len,
                "limit": bullet_limit,
                "is_valid": b_len <= bullet_limit,
                "message": (
                    f"Bullet {i + 1} OK ({b_len}/{bullet_limit} chars)"
                    if b_len <= bullet_limit
                    else f"Bullet {i + 1} exceeds limit by {b_len - bullet_limit} chars"
                ),
            })

    # --- Key Features (Flipkart) ---
    if marketplace == "flipkart" and content.key_features:
        feature_limit = limits.get("key_feature_max_chars", 200)
        for i, feature in enumerate(content.key_features):
            f_len = len(feature)
            results.append({
                "field": f"key_feature_{i + 1}",
                "value": feature[:80] + ("..." if f_len > 80 else ""),
                "length": f_len,
                "limit": feature_limit,
                "is_valid": f_len <= feature_limit,
                "message": (
                    f"Key feature {i + 1} OK ({f_len}/{feature_limit} chars)"
                    if f_len <= feature_limit
                    else f"Key feature {i + 1} exceeds limit by {f_len - feature_limit} chars"
                ),
            })

    # --- Description ---
    desc_limit = limits.get("description_max_chars", 2000)
    desc_len = len(content.description)
    results.append({
        "field": "description",
        "value": content.description[:80] + ("..." if desc_len > 80 else ""),
        "length": desc_len,
        "limit": desc_limit,
        "is_valid": desc_len <= desc_limit,
        "message": (
            f"Description OK ({desc_len}/{desc_limit} chars)"
            if desc_len <= desc_limit
            else f"Description exceeds limit by {desc_len - desc_limit} chars ({desc_len}/{desc_limit})"
        ),
    })

    # --- Search Terms / Keywords ---
    if marketplace == "amazon" and content.search_terms:
        st_limit = limits.get("search_terms_max_bytes", 250)
        st_bytes = len(content.search_terms.encode("utf-8"))
        results.append({
            "field": "search_terms",
            "value": content.search_terms[:80] + ("..." if len(content.search_terms) > 80 else ""),
            "length": st_bytes,
            "limit": st_limit,
            "is_valid": st_bytes <= st_limit,
            "message": (
                f"Search terms OK ({st_bytes}/{st_limit} bytes)"
                if st_bytes <= st_limit
                else f"Search terms exceeds limit by {st_bytes - st_limit} bytes"
            ),
        })

    if marketplace == "flipkart" and content.keywords:
        kw_limit = limits.get("search_keywords_max_chars", 500)
        kw_len = len(content.keywords)
        results.append({
            "field": "keywords",
            "value": content.keywords[:80] + ("..." if kw_len > 80 else ""),
            "length": kw_len,
            "limit": kw_limit,
            "is_valid": kw_len <= kw_limit,
            "message": (
                f"Keywords OK ({kw_len}/{kw_limit} chars)"
                if kw_len <= kw_limit
                else f"Keywords exceeds limit by {kw_len - kw_limit} chars"
            ),
        })

    return results


# ============================================================================
# Gemini API Call with Retry Logic
# ============================================================================

_MAX_RETRIES = 5
_BACKOFF_SECONDS = [1, 2, 4, 8, 16]  # exponential backoff: 1s, 2s, 4s, 8s, 16s


async def _call_gemini(prompt: str) -> dict[str, Any]:
    """Call the Gemini API with retry logic for rate-limit (429) and temporary unavailable (503) errors.

    Uses ``settings.GEMINI_MODEL`` for model selection and requests structured
    JSON output.

    Args:
        prompt: The full prompt string to send to Gemini.

    Returns:
        Parsed JSON dict from Gemini's response.

    Raises:
        ValueError: If Gemini API key is not configured.
        RuntimeError: If all retries are exhausted or a non-retryable error occurs.
    """
    api_key = settings.GEMINI_API_KEY or await get_setting("gemini_api_key")
    if not api_key:
        raise ValueError(
            "Gemini API key not configured. Go to Settings to add your key."
        )

    client = genai.Client(api_key=api_key)
    last_error: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)

        except Exception as exc:
            last_error = exc
            exc_str = str(exc).lower()

            # Retry on rate-limit (429), resource exhausted, 503 unavailable, or overload errors
            should_retry = (
                "429" in exc_str or 
                "503" in exc_str or 
                "unavailable" in exc_str or 
                ("resource" in exc_str and "exhausted" in exc_str) or
                "overloaded" in exc_str
            )

            if should_retry:
                wait = _BACKOFF_SECONDS[attempt] if attempt < len(_BACKOFF_SECONDS) else _BACKOFF_SECONDS[-1]
                logger.warning(
                    "Gemini API transient issue (attempt %d/%d). Retrying in %ds: %s",
                    attempt + 1, _MAX_RETRIES, wait, exc,
                )
                await asyncio.sleep(wait)
                continue

            # Non-retryable error – raise immediately
            logger.error("Gemini API error (non-retryable): %s", exc)
            raise RuntimeError(f"Gemini content generation failed: {exc}") from exc

    # All retries exhausted
    raise RuntimeError(
        f"Gemini content generation failed after {_MAX_RETRIES} retries: {last_error}"
    )


# ============================================================================
# Content Parsing Helpers
# ============================================================================

def _parse_amazon_content(raw: dict[str, Any]) -> MarketplaceContent:
    """Parse raw Gemini JSON output into a MarketplaceContent for Amazon.

    Args:
        raw: Parsed JSON dict from Gemini.

    Returns:
        Populated MarketplaceContent instance.
    """
    return MarketplaceContent(
        title=raw.get("title", ""),
        bullets=raw.get("bullets", []),
        description=raw.get("description", ""),
        search_terms=raw.get("search_terms", ""),
    )


def _parse_flipkart_content(raw: dict[str, Any]) -> MarketplaceContent:
    """Parse raw Gemini JSON output into a MarketplaceContent for Flipkart.

    Args:
        raw: Parsed JSON dict from Gemini.

    Returns:
        Populated MarketplaceContent instance.
    """
    return MarketplaceContent(
        title=raw.get("title", ""),
        key_features=raw.get("key_features", []),
        description=raw.get("description", ""),
        keywords=raw.get("keywords", ""),
    )


def _parse_meesho_content(raw: dict[str, Any]) -> MarketplaceContent:
    """Parse raw Gemini JSON output into a MarketplaceContent for Meesho.

    Args:
        raw: Parsed JSON dict from Gemini.

    Returns:
        Populated MarketplaceContent instance.
    """
    return MarketplaceContent(
        title=raw.get("title", ""),
        description=raw.get("description", ""),
    )


def _validate_and_warn(content: MarketplaceContent, marketplace: str) -> None:
    """Run validation and log warnings for any fields exceeding limits.

    Args:
        content: Generated marketplace content.
        marketplace: Target marketplace name.
    """
    issues = validate_content(content, marketplace)
    for item in issues:
        if not item["is_valid"]:
            logger.warning(
                "⚠️  %s/%s limit exceeded: %s",
                marketplace, item["field"], item["message"],
            )


# ============================================================================
# Main Generation Function
# ============================================================================

async def generate_marketplace_content(
    product_details: dict[str, Any],
    keywords: list[str],
    marketplace: str = "all",
    variation_info: dict[str, str] | None = None,
) -> ContentGenerationResponse:
    """Generate e-commerce listing copy optimized for Indian marketplaces.

    Calls the Gemini API with marketplace-specific prompts and validates
    the output against character limits. Supports generating content for
    a specific product variant when ``variation_info`` is provided.

    Args:
        product_details: Product specs (name, brand, category, notes, dimensions).
        keywords: Curated list of target keywords to inject.
        marketplace: Target platform (``amazon``, ``flipkart``, ``meesho``, or ``all``).
        variation_info: Optional dict with ``variation_type`` and ``variation_value``
            to generate variant-specific content.

    Returns:
        ``ContentGenerationResponse`` with populated marketplace content objects.

    Raises:
        ValueError: If Gemini API key is not configured.
        RuntimeError: If Gemini API call fails after retries.
    """
    name = product_details.get("name", "Product")
    logger.info(
        "✍️ Invoking Gemini Content Generation for: '%s' (MP: %s, variation: %s)",
        name, marketplace, variation_info,
    )

    # Map marketplace → (prompt_builder, parser)
    _builders: dict[str, tuple] = {
        "amazon": (_build_amazon_prompt, _parse_amazon_content),
        "flipkart": (_build_flipkart_prompt, _parse_flipkart_content),
        "meesho": (_build_meesho_prompt, _parse_meesho_content),
    }

    targets = list(_builders.keys()) if marketplace == "all" else [marketplace]
    results: dict[str, MarketplaceContent | None] = {
        "amazon": None, "flipkart": None, "meesho": None,
    }

    for mp in targets:
        builder, parser = _builders[mp]
        prompt = builder(product_details, keywords, variation_info)
        raw_json = await _call_gemini(prompt)
        content = parser(raw_json)

        # Validate and log warnings for exceeded limits
        _validate_and_warn(content, mp)
        results[mp] = content

    return ContentGenerationResponse(
        amazon=results["amazon"],
        flipkart=results["flipkart"],
        meesho=results["meesho"],
    )


# ============================================================================
# Variation-Aware Batch Generation
# ============================================================================

async def generate_content_with_variations(
    product_details: dict[str, Any],
    keywords: list[str],
    variations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate content for the base product plus all its variations.

    First generates base content for all 3 marketplaces, then generates
    adapted content for each variation (customizing title and first
    bullet/feature for the specific variant).

    Args:
        product_details: Base product specs dict from DB.
        keywords: Curated list of target keywords.
        variations: List of variation dicts from the DB, each containing
            ``id``, ``variation_type``, and ``variation_value``.

    Returns:
        Dict with structure::

            {
                "base": ContentGenerationResponse,
                "variations": {
                    <variation_id>: ContentGenerationResponse,
                    ...
                }
            }

    Raises:
        ValueError: If Gemini API key is not configured.
        RuntimeError: If Gemini API call fails after retries.
    """
    logger.info(
        "🔄 Generating content with %d variations for: '%s'",
        len(variations), product_details.get("name", "Product"),
    )

    # 1. Generate base content for all 3 marketplaces
    base_content = await generate_marketplace_content(
        product_details=product_details,
        keywords=keywords,
        marketplace="all",
    )

    # 2. Generate variation-specific content for each variant
    variation_results: dict[int, ContentGenerationResponse] = {}

    for variation in variations:
        var_id = variation["id"]
        var_info = {
            "variation_type": variation.get("variation_type", "variant"),
            "variation_value": variation.get("variation_value", ""),
        }

        logger.info(
            "  ↳ Generating variation content: %s=%s (id=%d)",
            var_info["variation_type"], var_info["variation_value"], var_id,
        )

        var_content = await generate_marketplace_content(
            product_details=product_details,
            keywords=keywords,
            marketplace="all",
            variation_info=var_info,
        )
        variation_results[var_id] = var_content

    return {
        "base": base_content,
        "variations": variation_results,
    }
