"""
Async SQLite database layer for Listing Helper.

Provides connection management, schema initialisation, and CRUD helper
functions using aiosqlite with Row-factory for dict-like access.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import aiosqlite

from config import settings

logger = logging.getLogger("listing_helper.database")

DATABASE_PATH = Path(settings.DATABASE_PATH)

# ============================================================================
# Connection Management
# ============================================================================

@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that yields an aiosqlite connection.

    The connection uses ``aiosqlite.Row`` row-factory so that rows
    behave like dicts (accessible by column name).

    Usage::

        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM products")
            rows = await cursor.fetchall()
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DATABASE_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


# ============================================================================
# Schema Initialisation
# ============================================================================

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sku             TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    brand           TEXT,
    category        TEXT,
    subcategory     TEXT,
    cost_price      REAL,
    weight_grams    REAL,
    length_cm       REAL,
    width_cm        REAL,
    height_cm       REAL,
    hsn_code        TEXT,
    gst_rate        REAL DEFAULT 18.0,

    -- Amazon
    amazon_title        TEXT,
    amazon_bullets      TEXT,   -- JSON array
    amazon_description  TEXT,
    amazon_search_terms TEXT,
    amazon_asin         TEXT,
    amazon_status       TEXT DEFAULT 'draft',
    amazon_price        REAL,

    -- Flipkart
    flipkart_title           TEXT,
    flipkart_key_features    TEXT,   -- JSON array
    flipkart_description     TEXT,
    flipkart_search_keywords TEXT,
    flipkart_fsn             TEXT,
    flipkart_status          TEXT DEFAULT 'draft',
    flipkart_price           REAL,

    -- Meesho
    meesho_title       TEXT,
    meesho_description TEXT,
    meesho_group_id    TEXT,
    meesho_product_id  TEXT,
    meesho_status      TEXT DEFAULT 'draft',
    meesho_price       REAL,

    -- Structured data
    keywords_data   TEXT,   -- JSON
    competitor_data TEXT,   -- JSON

    -- Workflow tracking (v2.0)
    listing_status  TEXT DEFAULT 'new',
    -- Values: 'new' → 'keywords_done' → 'content_ready' → 'priced' → 'exported' → 'listed'

    notes       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_variations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    variation_type  TEXT NOT NULL,
    variation_value TEXT NOT NULL,
    sku             TEXT,
    additional_cost REAL DEFAULT 0,
    stock_quantity  INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Per-variation marketplace content (v2.0)
CREATE TABLE IF NOT EXISTS variation_content (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variation_id    INTEGER NOT NULL,
    marketplace     TEXT NOT NULL,
    title           TEXT,
    bullets         TEXT,   -- JSON array
    description     TEXT,
    keywords        TEXT,
    status          TEXT DEFAULT 'draft',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variation_id) REFERENCES product_variations(id) ON DELETE CASCADE,
    UNIQUE(variation_id, marketplace)
);

CREATE TABLE IF NOT EXISTS export_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER,
    marketplace TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    export_type TEXT,
    status      TEXT DEFAULT 'completed',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pricing_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    marketplace     TEXT NOT NULL,
    selling_price   REAL,
    fees_breakdown  TEXT,   -- JSON
    profit          REAL,
    margin_percent  REAL,
    calculated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS keyword_researches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    seed_keyword  TEXT NOT NULL,
    product_id    INTEGER,
    results       TEXT NOT NULL,   -- JSON containing primary, secondary, etc.
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

-- App-level key-value settings (v2.0)
CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to auto-update updated_at on products
CREATE TRIGGER IF NOT EXISTS trg_products_updated_at
    AFTER UPDATE ON products
    FOR EACH ROW
BEGIN
    UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
"""

# Migrations for existing databases (v2.0)
_MIGRATIONS_SQL = [
    "ALTER TABLE products ADD COLUMN listing_status TEXT DEFAULT 'new'",
    "ALTER TABLE keyword_researches ADD COLUMN product_id INTEGER REFERENCES products(id)",
]


async def init_db() -> None:
    """Create all tables and triggers if they don't already exist.

    Also runs safe ALTER TABLE migrations for databases created before v2.0.
    """
    async with get_db() as db:
        await db.executescript(_SCHEMA_SQL)
        await db.commit()

        # Run migrations (safe – ignores 'duplicate column' errors)
        for migration in _MIGRATIONS_SQL:
            try:
                await db.execute(migration)
                await db.commit()
            except Exception:
                pass  # Column already exists

    logger.info("Database initialised at %s", DATABASE_PATH)


# ============================================================================
# JSON Helper
# ============================================================================

def _parse_json_field(value: str | None) -> Any:
    """Safely parse a JSON string; return None on failure."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    """Convert an ``aiosqlite.Row`` to a plain dict, parsing JSON columns."""
    d = dict(row)
    for json_col in (
        "amazon_bullets",
        "flipkart_key_features",
        "keywords_data",
        "competitor_data",
    ):
        if json_col in d:
            d[json_col] = _parse_json_field(d[json_col])
    return d


# ============================================================================
# Product CRUD
# ============================================================================

async def get_product(product_id: int) -> Optional[dict[str, Any]]:
    """Fetch a single product by ID.

    Args:
        product_id: Primary key of the product.

    Returns:
        Product dict or ``None`` if not found.
    """
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_dict(row)


async def get_all_products(
    *,
    category: Optional[str] = None,
    marketplace_status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch products with optional filtering and pagination.

    Args:
        category: Filter by category (exact match).
        marketplace_status: Filter by status across any marketplace,
            format ``marketplace:status`` e.g. ``amazon:draft``.
        search: Free-text search across name, sku, brand.
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        Tuple of (list of product dicts, total matching count).
    """
    conditions: list[str] = []
    params: list[Any] = []

    if category:
        if category == "home_kitchen_general":
            conditions.append("(category = ? OR category = ?)")
            params.extend(["home_kitchen_general", "home_kitchen"])
        else:
            conditions.append("category = ?")
            params.append(category)

    if marketplace_status:
        parts = marketplace_status.split(":")
        if len(parts) == 2:
            mp, status = parts
            col = f"{mp}_status"
            conditions.append(f"{col} = ?")
            params.append(status)

    if search:
        conditions.append("(name LIKE ? OR sku LIKE ? OR brand LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with get_db() as db:
        # Total count
        count_cursor = await db.execute(f"SELECT COUNT(*) as cnt FROM products {where}", params)
        total = (await count_cursor.fetchone())["cnt"]

        # Paginated rows
        offset = (page - 1) * per_page
        query = f"SELECT * FROM products {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        cursor = await db.execute(query, [*params, per_page, offset])
        rows = await cursor.fetchall()

    return [_row_to_dict(r) for r in rows], total


async def create_product(data: dict[str, Any]) -> dict[str, Any]:
    """Insert a new product and return the created row.

    JSON-serialisable fields (bullets, features, keywords_data, etc.)
    are automatically serialised.

    Args:
        data: Dictionary of column→value pairs.

    Returns:
        The newly created product dict.

    Raises:
        aiosqlite.IntegrityError: If the SKU already exists.
    """
    # Serialise JSON fields
    for json_col in ("amazon_bullets", "flipkart_key_features", "keywords_data", "competitor_data"):
        if json_col in data and not isinstance(data[json_col], str):
            data[json_col] = json.dumps(data[json_col]) if data[json_col] is not None else None

    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    values = list(data.values())

    async with get_db() as db:
        cursor = await db.execute(
            f"INSERT INTO products ({columns}) VALUES ({placeholders})",
            values,
        )
        await db.commit()
        product_id = cursor.lastrowid

    logger.info("Created product id=%d sku=%s", product_id, data.get("sku"))
    return await get_product(product_id)  # type: ignore[return-value]


async def update_product(product_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Partially update a product.

    Only keys present in ``data`` are updated; ``None``-valued keys are
    skipped to avoid overwriting with NULL unintentionally.

    Args:
        product_id: Product primary key.
        data: Column→value mapping of fields to update.

    Returns:
        Updated product dict, or ``None`` if product doesn't exist.
    """
    # Filter out None values and empty keys
    updates = {k: v for k, v in data.items() if v is not None}
    if not updates:
        return await get_product(product_id)

    # Serialise JSON fields
    for json_col in ("amazon_bullets", "flipkart_key_features", "keywords_data", "competitor_data"):
        if json_col in updates and not isinstance(updates[json_col], str):
            updates[json_col] = json.dumps(updates[json_col])

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [product_id]

    async with get_db() as db:
        await db.execute(
            f"UPDATE products SET {set_clause} WHERE id = ?",
            values,
        )
        await db.commit()

    logger.info("Updated product id=%d fields=%s", product_id, list(updates.keys()))
    return await get_product(product_id)


async def delete_product(product_id: int) -> bool:
    """Delete a product by ID.

    Args:
        product_id: Product primary key.

    Returns:
        ``True`` if a row was deleted, ``False`` otherwise.
    """
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()
        deleted = cursor.rowcount > 0

    if deleted:
        logger.info("Deleted product id=%d", product_id)
    return deleted


async def search_products(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Quick search across name, sku, and brand.

    Args:
        query: Search term.
        limit: Maximum results to return.

    Returns:
        List of matching product dicts.
    """
    like = f"%{query}%"
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM products WHERE name LIKE ? OR sku LIKE ? OR brand LIKE ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (like, like, like, limit),
        )
        rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


# ============================================================================
# Variation CRUD
# ============================================================================

async def get_variations(product_id: int) -> list[dict[str, Any]]:
    """Get all variations for a product."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM product_variations WHERE product_id = ? ORDER BY id",
            (product_id,),
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def create_variation(product_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Insert a new variation for a product."""
    data["product_id"] = product_id
    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    values = list(data.values())

    async with get_db() as db:
        cursor = await db.execute(
            f"INSERT INTO product_variations ({columns}) VALUES ({placeholders})",
            values,
        )
        await db.commit()
        var_id = cursor.lastrowid

        row_cursor = await db.execute(
            "SELECT * FROM product_variations WHERE id = ?", (var_id,)
        )
        row = await row_cursor.fetchone()

    logger.info("Created variation id=%d for product id=%d", var_id, product_id)
    return dict(row)


async def delete_variation(variation_id: int) -> bool:
    """Delete a variation by ID."""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM product_variations WHERE id = ?", (variation_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


# ============================================================================
# Export History
# ============================================================================

async def get_export_history(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve recent export history entries."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM export_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def create_export_record(data: dict[str, Any]) -> dict[str, Any]:
    """Insert an export history record."""
    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    values = list(data.values())

    async with get_db() as db:
        cursor = await db.execute(
            f"INSERT INTO export_history ({columns}) VALUES ({placeholders})",
            values,
        )
        await db.commit()
        row_cursor = await db.execute(
            "SELECT * FROM export_history WHERE id = ?", (cursor.lastrowid,)
        )
        row = await row_cursor.fetchone()
    return dict(row)


# ============================================================================
# Pricing Snapshots
# ============================================================================

async def save_pricing_snapshot(data: dict[str, Any]) -> int:
    """Save a pricing calculation snapshot.

    Returns:
        ID of the new snapshot row.
    """
    if "fees_breakdown" in data and not isinstance(data["fees_breakdown"], str):
        data["fees_breakdown"] = json.dumps(data["fees_breakdown"])

    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    values = list(data.values())

    async with get_db() as db:
        cursor = await db.execute(
            f"INSERT INTO pricing_snapshots ({columns}) VALUES ({placeholders})",
            values,
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


# ============================================================================
# Dashboard Stats
# ============================================================================

async def get_dashboard_stats() -> dict[str, Any]:
    """Aggregate statistics for the dashboard overview.

    Returns:
        Dict with total products, per-marketplace status counts, and
        recent activity timestamps.
    """
    async with get_db() as db:
        # Total products
        cur = await db.execute("SELECT COUNT(*) as cnt FROM products")
        total = (await cur.fetchone())["cnt"]

        # Per-marketplace status breakdown
        stats: dict[str, Any] = {"total_products": total, "marketplaces": {}}

        for mp in ("amazon", "flipkart", "meesho"):
            col = f"{mp}_status"
            cur = await db.execute(
                f"SELECT {col} as status, COUNT(*) as cnt FROM products GROUP BY {col}"
            )
            rows = await cur.fetchall()
            stats["marketplaces"][mp] = {r["status"]: r["cnt"] for r in rows}

        # Recent activity (last 10 updated products)
        cur = await db.execute(
            "SELECT id, sku, name, updated_at FROM products ORDER BY updated_at DESC LIMIT 10"
        )
        stats["recent_activity"] = [dict(r) for r in await cur.fetchall()]

    return stats


# ============================================================================
# Keyword Research Cache
# ============================================================================

async def get_keyword_research(seed_keyword: str, product_id: Optional[int] = None) -> Optional[dict[str, Any]]:
    """Fetch saved keyword research results by seed keyword or product_id."""
    async with get_db() as db:
        if product_id:
            cursor = await db.execute(
                "SELECT * FROM keyword_researches WHERE product_id = ? ORDER BY created_at DESC LIMIT 1",
                (product_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM keyword_researches WHERE seed_keyword = ? ORDER BY created_at DESC LIMIT 1",
                (seed_keyword.lower().strip(),),
            )
        row = await cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["results"] = _parse_json_field(d["results"])
        return d


async def save_keyword_research(
    seed_keyword: str, results: dict[str, Any], product_id: Optional[int] = None
) -> dict[str, Any]:
    """Save keyword research results, optionally linked to a product."""
    seed = seed_keyword.lower().strip()
    results_json = json.dumps(results)

    async with get_db() as db:
        cursor = await db.execute(
            "INSERT OR REPLACE INTO keyword_researches (seed_keyword, product_id, results) VALUES (?, ?, ?)",
            (seed, product_id, results_json),
        )
        rec_id = cursor.lastrowid
        await db.commit()

        row_cursor = await db.execute(
            "SELECT * FROM keyword_researches WHERE id = ?", (rec_id,)
        )
        res_row = await row_cursor.fetchone()

    d = dict(res_row)
    d["results"] = _parse_json_field(d["results"])
    return d


async def get_all_keyword_researches(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve recent keyword research records."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM keyword_researches ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d["results"] = _parse_json_field(d["results"])
        results.append(d)
    return results


# ============================================================================
# Variation Content CRUD (v2.0)
# ============================================================================

async def get_variation_content(variation_id: int, marketplace: Optional[str] = None) -> list[dict[str, Any]]:
    """Get marketplace content for a product variation.

    Args:
        variation_id: Variation primary key.
        marketplace: Optional filter for specific marketplace.

    Returns:
        List of variation content dicts.
    """
    async with get_db() as db:
        if marketplace:
            cursor = await db.execute(
                "SELECT * FROM variation_content WHERE variation_id = ? AND marketplace = ?",
                (variation_id, marketplace),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM variation_content WHERE variation_id = ? ORDER BY marketplace",
                (variation_id,),
            )
        rows = await cursor.fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d["bullets"] = _parse_json_field(d.get("bullets"))
        results.append(d)
    return results


async def save_variation_content(variation_id: int, marketplace: str, data: dict[str, Any]) -> dict[str, Any]:
    """Save or update marketplace content for a variation (upsert).

    Args:
        variation_id: Variation primary key.
        marketplace: Target marketplace.
        data: Content fields (title, bullets, description, keywords).

    Returns:
        Saved content dict.
    """
    if "bullets" in data and not isinstance(data.get("bullets"), str):
        data["bullets"] = json.dumps(data["bullets"]) if data["bullets"] else None

    async with get_db() as db:
        # Check if exists
        cursor = await db.execute(
            "SELECT id FROM variation_content WHERE variation_id = ? AND marketplace = ?",
            (variation_id, marketplace),
        )
        existing = await cursor.fetchone()

        if existing:
            set_parts = []
            values = []
            for key in ("title", "bullets", "description", "keywords", "status"):
                if key in data:
                    set_parts.append(f"{key} = ?")
                    values.append(data[key])
            if set_parts:
                values.append(existing["id"])
                await db.execute(
                    f"UPDATE variation_content SET {', '.join(set_parts)} WHERE id = ?",
                    values,
                )
            rec_id = existing["id"]
        else:
            data["variation_id"] = variation_id
            data["marketplace"] = marketplace
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            cursor = await db.execute(
                f"INSERT INTO variation_content ({columns}) VALUES ({placeholders})",
                list(data.values()),
            )
            rec_id = cursor.lastrowid

        await db.commit()

        row_cursor = await db.execute(
            "SELECT * FROM variation_content WHERE id = ?", (rec_id,)
        )
        row = await row_cursor.fetchone()

    d = dict(row)
    d["bullets"] = _parse_json_field(d.get("bullets"))
    return d


async def get_all_variation_content_for_product(product_id: int) -> list[dict[str, Any]]:
    """Get all variation content across all variations for a product."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT vc.*, pv.variation_type, pv.variation_value, pv.sku as variation_sku
               FROM variation_content vc
               JOIN product_variations pv ON pv.id = vc.variation_id
               WHERE pv.product_id = ?
               ORDER BY pv.id, vc.marketplace""",
            (product_id,),
        )
        rows = await cursor.fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d["bullets"] = _parse_json_field(d.get("bullets"))
        results.append(d)
    return results


# ============================================================================
# App Settings (v2.0)
# ============================================================================

async def get_setting(key: str) -> Optional[str]:
    """Get a single app setting by key."""
    async with get_db() as db:
        cursor = await db.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else None


async def set_setting(key: str, value: str) -> None:
    """Set an app setting (upsert)."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP",
            (key, value, value),
        )
        await db.commit()


async def get_all_settings() -> dict[str, str]:
    """Get all app settings as a dict."""
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value FROM app_settings")
        rows = await cursor.fetchall()
    return {r["key"]: r["value"] for r in rows}

