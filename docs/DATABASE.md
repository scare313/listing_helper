# Database

SQLite database at `data/listing_helper.db`. Async access via `aiosqlite`.
Connection settings: WAL journal mode, foreign keys ON.

Schema is initialised in `database.py :: _SCHEMA_SQL`. Safe `ALTER TABLE` migrations
run at startup for databases created before v2.0.

---

## Tables

### products

Core product record. One row per product SKU.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment primary key |
| `sku` | TEXT UNIQUE | Seller SKU (e.g. `CAP-BLK-001`) |
| `name` | TEXT | Product name |
| `brand` | TEXT | Brand name |
| `category` | TEXT | One of the 6 category keys (see config.py) |
| `subcategory` | TEXT | Free-text subcategory |
| `cost_price` | REAL | Cost price in ₹ |
| `weight_grams` | REAL | Weight in grams (used for shipping fee calculation) |
| `length_cm` | REAL | Dimension |
| `width_cm` | REAL | Dimension |
| `height_cm` | REAL | Dimension |
| `hsn_code` | TEXT | Indian HSN classification code |
| `gst_rate` | REAL | GST percentage (default 18.0) |
| `amazon_title` | TEXT | Amazon listing title (max 200 chars) |
| `amazon_bullets` | TEXT | JSON array of 5 bullet points |
| `amazon_description` | TEXT | Amazon product description (max 2000 chars) |
| `amazon_search_terms` | TEXT | Backend search terms (max 250 bytes) |
| `amazon_asin` | TEXT | Amazon ASIN (once published) |
| `amazon_status` | TEXT | `draft`, `ready`, `listed` |
| `amazon_price` | REAL | Calculated selling price for Amazon in ₹ |
| `flipkart_title` | TEXT | Flipkart listing title (max 500 chars) |
| `flipkart_key_features` | TEXT | JSON array of up to 10 features |
| `flipkart_description` | TEXT | Flipkart product description (max 5000 chars) |
| `flipkart_search_keywords` | TEXT | Flipkart search keywords (max 500 chars) |
| `flipkart_fsn` | TEXT | Flipkart FSN (once published) |
| `flipkart_status` | TEXT | `draft`, `ready`, `listed` |
| `flipkart_price` | REAL | Calculated selling price for Flipkart in ₹ |
| `meesho_title` | TEXT | Meesho listing title (max 200 chars) |
| `meesho_description` | TEXT | Meesho product description (max 2000 chars) |
| `meesho_group_id` | TEXT | Meesho group ID (once published) |
| `meesho_product_id` | TEXT | Meesho product ID (once published) |
| `meesho_status` | TEXT | `draft`, `ready`, `listed` |
| `meesho_price` | REAL | Calculated selling price for Meesho in ₹ |
| `keywords_data` | TEXT | JSON object — `{applied_keywords: [...]}` |
| `competitor_data` | TEXT | JSON (reserved, not currently used) |
| `listing_status` | TEXT | Workflow stage (see state transitions below) |
| `notes` | TEXT | Free-text notes / special instructions for AI |
| `created_at` | TIMESTAMP | Auto-set on INSERT |
| `updated_at` | TIMESTAMP | Auto-updated by trigger `trg_products_updated_at` |

**Trigger**: `trg_products_updated_at` sets `updated_at = CURRENT_TIMESTAMP` on every UPDATE.

---

### product_variations

Color/size/material variants of a product. Each variation gets its own SKU and can have
tailored marketplace content.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `product_id` | INTEGER FK | References `products(id)` ON DELETE CASCADE |
| `variation_type` | TEXT | `color`, `size`, `material`, `style`, `other` |
| `variation_value` | TEXT | e.g. `Black`, `XL`, `Cotton` |
| `sku` | TEXT | Variation-specific SKU |
| `additional_cost` | REAL | Extra cost vs base product (default 0) |
| `stock_quantity` | INTEGER | Stock quantity (default 0) |
| `created_at` | TIMESTAMP | Auto-set on INSERT |

---

### variation_content

Marketplace-specific content tailored per variation. Added in v2.0.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `variation_id` | INTEGER FK | References `product_variations(id)` ON DELETE CASCADE |
| `marketplace` | TEXT | `amazon`, `flipkart`, or `meesho` |
| `title` | TEXT | Variation-adapted title |
| `bullets` | TEXT | JSON array (bullets for Amazon, key features for Flipkart) |
| `description` | TEXT | Variation-adapted description |
| `keywords` | TEXT | Search terms / keywords |
| `status` | TEXT | `draft` or `ready` |
| `created_at` | TIMESTAMP | Auto-set on INSERT |

**Unique constraint**: `(variation_id, marketplace)` — one row per variation per marketplace.
Saves use upsert logic in `save_variation_content()`.

---

### keyword_researches

Cache of keyword research results. Avoids re-scraping the same seed.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `seed_keyword` | TEXT | Lowercased seed keyword or URL |
| `product_id` | INTEGER FK | Optional link to product (added v2.0) |
| `results` | TEXT | JSON object — full NLP analysis result |
| `created_at` | TIMESTAMP | Auto-set on INSERT |

`results` JSON structure:
```json
{
  "primary": ["baseball cap", "cotton cap", ...],
  "secondary": ["adjustable baseball cap", ...],
  "long_tail": ["adjustable cap for men outdoor", ...],
  "trending": ["trending baseball cap", ...],
  "autocomplete": ["baseball cap men", ...],
  "metrics": {
    "frequencies": {"cap": 35, "men": 20, ...},
    "bi_grams": {"baseball cap": 15, ...},
    "tri_grams": {...},
    "four_grams": {...},
    "co_occurrences": [{"word_1": "men", "word_2": "adjustable", "count": 10}]
  },
  "scraped_count": 25,
  "total_links": 25
}
```

Cache lookup: by `(seed_keyword, product_id)` — most recent row wins. The `force_refresh=true`
query parameter bypasses the cache and triggers a fresh scrape.

---

### pricing_snapshots

Historical record of every pricing calculation. Useful for auditing price changes over time.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `product_id` | INTEGER FK | References `products(id)` ON DELETE CASCADE |
| `marketplace` | TEXT | `amazon`, `flipkart`, or `meesho` |
| `selling_price` | REAL | Calculated selling price in ₹ |
| `fees_breakdown` | TEXT | JSON object — per-fee line items |
| `profit` | REAL | Profit in ₹ |
| `margin_percent` | REAL | Actual achieved margin percentage |
| `calculated_at` | TIMESTAMP | Auto-set on INSERT |

Three rows are inserted per pricing call (one per marketplace).

---

### export_history

Audit trail of every Excel file generated.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `product_id` | INTEGER FK | References `products(id)` ON DELETE SET NULL |
| `marketplace` | TEXT | `all`, `amazon`, `flipkart`, or `meesho` |
| `file_path` | TEXT | Absolute path to the generated .xlsx file |
| `export_type` | TEXT | `template` (only type currently) |
| `status` | TEXT | `completed` |
| `created_at` | TIMESTAMP | Auto-set on INSERT |

Note: `product_id` is set to NULL if the referenced product is deleted (SET NULL semantics).
If multiple products are exported together, one row is written per product.

---

### app_settings

Key-value store for runtime configuration. Values written here take precedence over `.env`
defaults for settings that support DB override.

| Column | Type | Description |
|---|---|---|
| `key` | TEXT PK | Setting key (e.g. `gemini_api_key`) |
| `value` | TEXT | String value |
| `updated_at` | TIMESTAMP | Last write time |

Upsert: `INSERT OR REPLACE ... ON CONFLICT(key) DO UPDATE SET value = ?`

**Settings that support DB override** (read via `get_setting(key)` at call time):
- `gemini_api_key` — used by content_generator.py and vision_detector.py
- `headless_browser` — used by keyword_research.py (Selenium path)
- `scraper_min_delay` — used by keyword_research.py
- `scraper_max_delay` — used by keyword_research.py

**Settings that do NOT support DB override** (`.env` only):
- `APP_HOST`, `APP_PORT` — read at startup, cannot change without restart
- `DATABASE_PATH`, `EXPORT_PATH`, `UPLOAD_PATH` — path config, restart required

---

## Entity Relationships

```
products (1)
    ├─── (N) product_variations
    │         └─── (N) variation_content
    ├─── (N) keyword_researches
    ├─── (N) pricing_snapshots
    └─── (N) export_history

app_settings — standalone key-value, no FK
```

All cascade rules:
- `product_variations` → `products`: ON DELETE CASCADE (delete product = delete all variations)
- `variation_content` → `product_variations`: ON DELETE CASCADE
- `keyword_researches` → `products`: ON DELETE SET NULL (keyword data preserved)
- `pricing_snapshots` → `products`: ON DELETE CASCADE
- `export_history` → `products`: ON DELETE SET NULL (export records preserved)

---

## Workflow State Transitions

`products.listing_status` tracks the product through the wizard pipeline:

```
new
 │  Step 1 complete (product saved)
 ▼
keywords_done
 │  Step 2 complete (keywords applied to product)
 ▼
content_ready
 │  Step 3 complete (AI content saved, amazon/flipkart/meesho_status = 'ready')
 ▼
priced
 │  Step 4 complete (POST /pricing/calculate or /pricing/auto-price/{id})
 ▼
exported
 │  Step 5 complete (Excel downloaded via finishWizard())
 ▼
listed
   Step 5 "Mark as Listed" checkboxes checked
   → per-marketplace: amazon_status / flipkart_status / meesho_status = 'listed'
```

The `listing_status` column also drives the Kanban board on the dashboard. Products can be
manually moved between columns via Kanban drag-and-drop (PUT `/api/products/{id}` with
`listing_status`).

---

## Migrations

On startup, `init_db()` runs `_MIGRATIONS_SQL` — a list of safe `ALTER TABLE` statements that
are silently ignored if the column already exists:

```sql
ALTER TABLE products ADD COLUMN listing_status TEXT DEFAULT 'new'
ALTER TABLE keyword_researches ADD COLUMN product_id INTEGER REFERENCES products(id)
```

To add a future migration: append to `_MIGRATIONS_SQL` in `database.py`. The try/except
swallows `OperationalError: duplicate column name` so it is safe to re-run.

---

## JSON Columns

Several columns store JSON as TEXT. The `_parse_json_field()` helper in `database.py`
safely deserialises these on read. On write, `create_product()` and `update_product()` auto-
serialise Python lists/dicts for the known JSON columns.

Columns that store JSON arrays:
- `products.amazon_bullets`
- `products.flipkart_key_features`
- `variation_content.bullets`
- `keyword_researches.results`
- `pricing_snapshots.fees_breakdown`

Columns that store JSON objects:
- `products.keywords_data`
- `products.competitor_data`

**Technical debt**: `products.competitor_data` is defined in the schema and model but no
code currently writes to it. It is reserved for a future competitor analysis feature.
