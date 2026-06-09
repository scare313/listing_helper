"""
Configuration management for Listing Helper.

Loads environment variables from .env file and defines all application
constants including marketplace fee structures, category mappings,
and character limits.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)

logger = logging.getLogger("listing_helper.config")

# ============================================================================
# Application Settings
# ============================================================================

@dataclass(frozen=True)
class AppSettings:
    """Core application settings sourced from environment variables."""

    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Amazon SP-API
    AMAZON_SP_API_REFRESH_TOKEN: str = os.getenv("AMAZON_SP_API_REFRESH_TOKEN", "")
    AMAZON_SP_API_CLIENT_ID: str = os.getenv("AMAZON_SP_API_CLIENT_ID", "")
    AMAZON_SP_API_CLIENT_SECRET: str = os.getenv("AMAZON_SP_API_CLIENT_SECRET", "")
    AMAZON_MARKETPLACE_ID: str = os.getenv("AMAZON_MARKETPLACE_ID", "A21TJRUUN4KGV")

    # Flipkart API
    FLIPKART_APP_ID: str = os.getenv("FLIPKART_APP_ID", "")
    FLIPKART_APP_SECRET: str = os.getenv("FLIPKART_APP_SECRET", "")

    # App
    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/listing_helper.db")
    EXPORT_PATH: str = os.getenv("EXPORT_PATH", "data/exports")
    UPLOAD_PATH: str = os.getenv("UPLOAD_PATH", "data/uploads")
    DEFAULT_TARGET_MARGIN: float = float(os.getenv("DEFAULT_TARGET_MARGIN", "25"))
    HEADLESS_BROWSER: bool = os.getenv("HEADLESS_BROWSER", "True").lower() == "true"

    # Scraper Settings
    SCRAPER_MIN_DELAY: float = float(os.getenv("SCRAPER_MIN_DELAY", "2"))
    SCRAPER_MAX_DELAY: float = float(os.getenv("SCRAPER_MAX_DELAY", "4"))
    SCRAPER_MAX_RETRIES: int = int(os.getenv("SCRAPER_MAX_RETRIES", "2"))


settings = AppSettings()


# ============================================================================
# Rotating User Agents (realistic Chrome/Firefox on Windows/Mac)
# ============================================================================

SCRAPER_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# ============================================================================
# Amazon India Fee Structure
# ============================================================================

AMAZON_FEES: dict[str, Any] = {
    "referral_fees": {
        # category_key → percentage (decimal)
        "sports_and_fitness": 0.10,          # Baseball Caps
        "home_and_kitchen_low": 0.05,        # items ≤ ₹300
        "home_and_kitchen_mid": 0.09,        # items ₹301-₹500
        "home_and_kitchen_high": 0.12,       # items ₹501-₹1000
        "home_and_kitchen_premium": 0.15,    # items > ₹1000
        "default": 0.10,
    },
    "closing_fees": {
        # Slab → fee in ₹ (Easy Ship / FBA)
        "0-250": 4,
        "251-500": 9,
        "501-1000": 30,
        "1001-above": 61,
    },
    "weight_handling_fees": {
        # weight_slab_grams → fee in ₹ (Easy Ship – Standard, Local)
        "0-500_local": 29,
        "0-500_regional": 40,
        "0-500_national": 57,
        "500-1000_local": 40,
        "500-1000_regional": 55,
        "500-1000_national": 76,
        "1000-2000_local": 55,
        "1000-2000_regional": 75,
        "1000-2000_national": 100,
        "2000-5000_local": 80,
        "2000-5000_regional": 105,
        "2000-5000_national": 140,
    },
    "gst_on_fees": 0.18,  # 18 % GST on Amazon fees
}


# ============================================================================
# Flipkart Fee Structure
# ============================================================================

FLIPKART_FEES: dict[str, Any] = {
    "commission": {
        # category_key → percentage
        "sports_and_fitness": 0.08,          # Baseball Caps
        "home_and_kitchen_low": 0.06,        # items ≤ ₹300
        "home_and_kitchen_mid": 0.10,        # items ₹301-₹500
        "home_and_kitchen_high": 0.13,       # items ₹501-₹1000
        "home_and_kitchen_premium": 0.16,    # items > ₹1000
        "default": 0.10,
    },
    "fixed_fees": {
        # price slab → fee in ₹
        "0-250": 6,
        "251-500": 11,
        "501-1000": 24,
        "1001-above": 40,
    },
    "shipping_fees": {
        # weight_slab_grams + zone → fee in ₹
        "0-500_local": 29,
        "0-500_zonal": 40,
        "0-500_national": 57,
        "500-1000_local": 45,
        "500-1000_zonal": 60,
        "500-1000_national": 80,
        "1000-2000_local": 65,
        "1000-2000_zonal": 85,
        "1000-2000_national": 110,
        "2000-5000_local": 95,
        "2000-5000_zonal": 125,
        "2000-5000_national": 165,
    },
    "collection_fees": {
        # percentage of order value
        "percentage": 0.02,
        "min": 5,
        "max": 25,
    },
    "gst_on_fees": 0.18,
}


# ============================================================================
# Meesho Fee Structure
# ============================================================================

MEESHO_FEES: dict[str, Any] = {
    "commission": 0.0,  # 0 % commission – Meesho's core USP
    "shipping_fees": {
        # weight_slab_grams + zone → fee in ₹
        "0-500_local": 30,
        "0-500_zonal": 45,
        "0-500_national": 65,
        "500-1000_local": 45,
        "500-1000_zonal": 65,
        "500-1000_national": 85,
        "1000-2000_local": 65,
        "1000-2000_zonal": 90,
        "1000-2000_national": 120,
        "2000-5000_local": 100,
        "2000-5000_zonal": 135,
        "2000-5000_national": 170,
    },
    "gst_on_shipping": 0.18,
}


# ============================================================================
# Category Mappings
# ============================================================================

CATEGORY_MAPPINGS: dict[str, dict[str, str]] = {
    "baseball_caps": {
        "amazon": "Sports, Fitness & Outdoors > Baseball Caps",
        "flipkart": "Sports & Fitness > Accessories > Caps",
        "meesho": "Men Accessories > Caps & Hats",
        "fee_category_key": "sports_and_fitness",
    },
    "home_kitchen_general": {
        "amazon": "Home & Kitchen",
        "flipkart": "Home & Kitchen",
        "meesho": "Home & Kitchen",
        "fee_category_key": "home_and_kitchen_mid",
    },
    "kitchen_storage": {
        "amazon": "Home & Kitchen > Kitchen Storage & Containers",
        "flipkart": "Home & Kitchen > Kitchen Storage",
        "meesho": "Home & Kitchen > Kitchen Storage",
        "fee_category_key": "home_and_kitchen_mid",
    },
    "kitchen_tools": {
        "amazon": "Home & Kitchen > Kitchen Tools & Gadgets",
        "flipkart": "Home & Kitchen > Cookware & Bakeware > Kitchen Tools",
        "meesho": "Home & Kitchen > Kitchen Tools",
        "fee_category_key": "home_and_kitchen_mid",
    },
    "home_decor": {
        "amazon": "Home & Kitchen > Home Décor",
        "flipkart": "Home Furnishing > Home Décor",
        "meesho": "Home & Kitchen > Home Decor",
        "fee_category_key": "home_and_kitchen_high",
    },
    "cleaning_supplies": {
        "amazon": "Home & Kitchen > Cleaning Supplies",
        "flipkart": "Home & Kitchen > Cleaning & Bathroom Accessories",
        "meesho": "Home & Kitchen > Cleaning Supplies",
        "fee_category_key": "home_and_kitchen_low",
    },
}


# ============================================================================
# Marketplace Character / Field Limits
# ============================================================================

MARKETPLACE_LIMITS: dict[str, dict[str, int | dict[str, int]]] = {
    "amazon": {
        "title_max_chars": 200,
        "title_max_bytes": 500,
        "bullet_count": 5,
        "bullet_max_chars": 500,
        "description_max_chars": 2000,
        "search_terms_max_bytes": 250,
        "backend_keywords_max_bytes": 250,
    },
    "flipkart": {
        "title_max_chars": 500,
        "key_features_count": 10,
        "key_feature_max_chars": 200,
        "description_max_chars": 5000,
        "search_keywords_max_chars": 500,
    },
    "meesho": {
        "title_max_chars": 200,
        "description_max_chars": 2000,
    },
}


# ============================================================================
# Default Listing Settings
# ============================================================================

DEFAULT_SETTINGS: dict[str, Any] = {
    "default_brand": "",
    "default_gst_rate": 18.0,
    "default_target_margin": settings.DEFAULT_TARGET_MARGIN,
    "supported_marketplaces": ["amazon", "flipkart", "meesho"],
    "supported_categories": list(CATEGORY_MAPPINGS.keys()),
    "default_shipping_zone": "national",
}


def get_referral_fee_rate(marketplace: str, category_key: str, selling_price: float = 0) -> float:
    """Return the referral / commission rate for a given marketplace and category.

    For Home & Kitchen the rate depends on the selling price, so the
    ``selling_price`` parameter is used to pick the correct slab.

    Args:
        marketplace: One of ``amazon``, ``flipkart``, ``meesho``.
        category_key: Internal category key (e.g. ``sports_and_fitness``).
        selling_price: The listing selling price in ₹.

    Returns:
        Referral fee rate as a float between 0 and 1.
    """
    if marketplace == "meesho":
        return 0.0

    fee_dict = AMAZON_FEES["referral_fees"] if marketplace == "amazon" else FLIPKART_FEES["commission"]

    # If category is home_and_kitchen, determine slab by price
    if category_key.startswith("home_and_kitchen"):
        if selling_price <= 300:
            return fee_dict.get("home_and_kitchen_low", fee_dict["default"])
        elif selling_price <= 500:
            return fee_dict.get("home_and_kitchen_mid", fee_dict["default"])
        elif selling_price <= 1000:
            return fee_dict.get("home_and_kitchen_high", fee_dict["default"])
        else:
            return fee_dict.get("home_and_kitchen_premium", fee_dict["default"])

    return fee_dict.get(category_key, fee_dict["default"])


def get_closing_fee(marketplace: str, selling_price: float) -> float:
    """Return the closing / fixed fee for a price slab.

    Args:
        marketplace: ``amazon`` or ``flipkart``.
        selling_price: Listing selling price in ₹.

    Returns:
        Closing / fixed fee in ₹.
    """
    if marketplace == "meesho":
        return 0.0

    slab_dict = AMAZON_FEES["closing_fees"] if marketplace == "amazon" else FLIPKART_FEES["fixed_fees"]

    if selling_price <= 250:
        return slab_dict["0-250"]
    elif selling_price <= 500:
        return slab_dict["251-500"]
    elif selling_price <= 1000:
        return slab_dict["501-1000"]
    else:
        return slab_dict["1001-above"]


def get_shipping_fee(marketplace: str, weight_grams: float, zone: str = "national") -> float:
    """Return the shipping / weight-handling fee.

    Args:
        marketplace: ``amazon``, ``flipkart``, or ``meesho``.
        weight_grams: Product weight in grams.
        zone: Shipping zone – ``local``, ``regional``/``zonal``, or ``national``.

    Returns:
        Shipping fee in ₹.
    """
    if marketplace == "amazon":
        ship_dict = AMAZON_FEES["weight_handling_fees"]
        zone_key = zone if zone in ("local", "regional", "national") else "national"
    elif marketplace == "flipkart":
        ship_dict = FLIPKART_FEES["shipping_fees"]
        zone_key = zone if zone in ("local", "zonal", "national") else "national"
    else:
        ship_dict = MEESHO_FEES["shipping_fees"]
        zone_key = zone if zone in ("local", "zonal", "national") else "national"

    if weight_grams <= 500:
        slab = "0-500"
    elif weight_grams <= 1000:
        slab = "500-1000"
    elif weight_grams <= 2000:
        slab = "1000-2000"
    else:
        slab = "2000-5000"

    key = f"{slab}_{zone_key}"
    return ship_dict.get(key, ship_dict.get(f"{slab}_national", 0))
