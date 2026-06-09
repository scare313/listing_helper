# API Reference

All endpoints return `ApiResponse`:
```json
{"success": true, "message": "OK", "data": <payload>}
```
On error: `{"success": false, "message": "...", "detail": "..."}` with appropriate HTTP status.

Interactive docs available at `http://localhost:8000/docs` when the server is running.

---

## System

### GET /api/health

Health check.

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "data/listing_helper.db",
  "export_path": "data/exports"
}
```

---

## Products — /api/products

### GET /api/products/

List products with optional filters and pagination.

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `category` | string | — | Filter by category key (e.g. `baseball_caps`) |
| `status` | string | — | Filter by marketplace status, format `marketplace:status` (e.g. `amazon:draft`) |
| `search` | string | — | Free-text search across name, sku, brand |
| `page` | int | 1 | Page number |
| `per_page` | int | 50 | Items per page (max 200) |

**Response `data`**
```json
{
  "products": [...],
  "total": 47,
  "page": 1,
  "per_page": 50
}
```

---

### GET /api/products/stats/overview

Dashboard statistics.

**Response `data`**
```json
{
  "total_products": 47,
  "marketplaces": {
    "amazon": {"draft": 10, "ready": 25, "listed": 12},
    "flipkart": {...},
    "meesho": {...}
  },
  "recent_activity": [
    {"id": 1, "sku": "CAP-001", "name": "Baseball Cap", "updated_at": "2026-06-09 10:00:00"}
  ]
}
```

---

### GET /api/products/{product_id}

Get a single product with its variations.

**Path Parameters**: `product_id` (int)

**Response `data`**
```json
{
  "product": {<ProductResponse>},
  "variations": [{<VariationResponse>}, ...]
}
```

**Errors**
- `404` — Product not found

---

### POST /api/products/

Create a new product.

**Request Body** (`ProductCreate`)
```json
{
  "sku": "CAP-BLK-001",
  "name": "Adjustable Cotton Baseball Cap",
  "brand": "SportsBrand",
  "category": "baseball_caps",
  "cost_price": 150.0,
  "weight_grams": 120.0,
  "gst_rate": 18.0
}
```

**Response** — HTTP 201, `data` = `ProductResponse`

**Errors**
- `409` — SKU already exists

---

### PUT /api/products/{product_id}

Partial update. Only fields included in the request body are modified.

**Request Body** (`ProductUpdate`) — all fields optional:
```json
{
  "amazon_title": "...",
  "amazon_bullets": ["Bullet 1", "Bullet 2"],
  "listing_status": "content_ready"
}
```

**Errors**
- `404` — Product not found

---

### DELETE /api/products/{product_id}

Delete a product and all its variations (CASCADE).

**Errors**
- `404` — Product not found

---

### GET /api/products/{product_id}/variations

List all variations for a product.

**Response `data`** — array of `VariationResponse`
```json
[
  {"id": 1, "product_id": 5, "variation_type": "color", "variation_value": "Black", "sku": "CAP-BLK-001"}
]
```

---

### POST /api/products/{product_id}/variations

Add a variation to a product.

**Request Body** (`VariationCreate`)
```json
{
  "variation_type": "color",
  "variation_value": "Black",
  "sku": "CAP-BLK-001",
  "additional_cost": 0,
  "stock_quantity": 50
}
```

**Response** — HTTP 201, `data` = `VariationResponse`

---

### DELETE /api/products/{product_id}/variations/{variation_id}

Delete a variation.

**Errors**
- `404` — Variation not found

---

### GET /api/products/{product_id}/variation-content

Get all variation content for a product (all variations, all marketplaces).

**Response `data`** — array of `VariationContentResponse` with joined variation fields:
```json
[
  {
    "id": 1, "variation_id": 1, "marketplace": "amazon",
    "title": "...", "bullets": [...], "description": "...",
    "variation_type": "color", "variation_value": "Black", "variation_sku": "CAP-BLK-001"
  }
]
```

---

### PUT /api/products/{product_id}/variation-content

Update variation content for multiple variations and marketplaces in one call.

**Request Body** — nested dict: `{variation_id: {marketplace: {content_fields}}}`
```json
{
  "1": {
    "amazon": {"title": "...", "bullets": ["b1", "b2"], "description": "..."},
    "flipkart": {"title": "...", "bullets": ["f1", "f2"], "description": "..."},
    "meesho": {"title": "...", "description": "..."}
  }
}
```

Note: String bullets are auto-split on newlines (`\n`) server-side.

---

## Keywords — /api/keywords

### POST /api/keywords/research

Run keyword research (non-streaming). Returns cached results if available.

**Request Body** (`KeywordResearchRequest`)
```json
{
  "seed_keywords": ["baseball cap"],
  "category": "baseball_caps",
  "marketplace": "amazon",
  "limit": 50,
  "product_id": 5,
  "force_refresh": false
}
```

**Response `data`** — full NLP results object (see DATABASE.md for structure)

---

### GET /api/keywords/research/stream

SSE stream for keyword research with live progress updates.

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `seed` | string | Yes | Seed keyword or Amazon URL |
| `limit` | int | No (50) | Max products to scrape (10–100) |
| `product_id` | string | No | Product ID to link results to |
| `force_refresh` | bool | No (false) | Skip cache |

**Stream Events** (text/event-stream)

Each event is a JSON object:
```
data: {"step": "collecting_links", "current": 0, "total": 0, "message": "..."}
data: {"step": "scraping_product", "current": 5, "total": 25, "message": "..."}
data: {"step": "analyzing", "current": 0, "total": 0, "message": "..."}
data: {"step": "autocomplete", "current": 0, "total": 0, "message": "..."}
data: {"step": "complete", "current": 25, "total": 25, "message": "...", "results": {...}}
```

Step values: `collecting_links`, `scraping_product`, `analyzing`, `autocomplete`, `fallback`,
`complete`, `error`

The `results` field is only present on the `complete` event.

---

### GET /api/keywords/autocomplete

Amazon autocomplete suggestions.

**Query Parameters**: `q` (string, required) — search prefix

**Response `data`** — array of suggestion strings

---

### GET /api/keywords/history

Recent keyword research records.

**Query Parameters**: `limit` (int, default 50)

**Response `data`** — array of `{id, seed_keyword, created_at, results_preview: {primary_count, secondary_count, long_tail_count}}`

---

### POST /api/keywords/apply-to-product

Apply selected keywords to a product (saves to `keywords_data.applied_keywords`).

**Query Parameters**: `product_id` (int), `keywords` (string array)

Example: `POST /api/keywords/apply-to-product?product_id=5&keywords=baseball+cap&keywords=cotton+cap`

---

## Content — /api/content

### POST /api/content/generate

Generate marketplace content for a product using Gemini AI.

**Request Body** (`ContentGenerationRequest`)
```json
{
  "product_id": 5,
  "marketplace": "all",
  "keywords": ["baseball cap", "cotton cap", "adjustable cap"]
}
```

`marketplace` values: `amazon`, `flipkart`, `meesho`, `all`

If `keywords` is empty, applied keywords from `products.keywords_data` are used.

**Response `data`** (`ContentGenerationResponse`)
```json
{
  "amazon": {
    "title": "BRAND Adjustable Cotton Baseball Cap...",
    "bullets": ["COMFORT – ...", "ADJUSTABLE – ...", ...],
    "description": "...",
    "search_terms": "baseball cap cotton adjustable..."
  },
  "flipkart": {
    "title": "...",
    "key_features": ["Material: 100% Cotton", ...],
    "description": "...",
    "keywords": "baseball cap::cotton cap::adjustable cap..."
  },
  "meesho": {
    "title": "...",
    "description": "..."
  }
}
```

**Errors**
- `400` — Gemini API key not configured
- `404` — Product not found
- `502` — Gemini API call failed after retries

---

### POST /api/content/generate/all

Convenience alias that forces `marketplace = "all"`.

Same request/response as `/generate`.

---

### POST /api/content/generate-with-variations

Generate content for the base product AND all its variations.

**Request Body** (`GenerateWithVariationsRequest`)
```json
{
  "product_id": 5,
  "keywords": ["baseball cap", "cotton cap"],
  "marketplace": "all"
}
```

**Response `data`**
```json
{
  "base": {<ContentGenerationResponse>},
  "variations": {
    "1": {<ContentGenerationResponse for variation id=1>},
    "2": {<ContentGenerationResponse for variation id=2>}
  }
}
```

Saves base content to `products` table and variation content to `variation_content` table.

**Errors**
- `404` — Product not found, or product has no variations
- `400` — Gemini API key not configured
- `502` — Gemini API call failed

---

### POST /api/content/validate

Validate listing content against marketplace character limits.

**Request Body** (`ValidateContentRequest`)
```json
{
  "marketplace": "amazon",
  "title": "My product title...",
  "bullets": ["Bullet 1", "Bullet 2"],
  "description": "Product description...",
  "keywords": "search terms here"
}
```

**Response `data`**
```json
{
  "marketplace": "amazon",
  "all_valid": false,
  "fields": [
    {
      "field": "title",
      "value": "My product title...",
      "length": 220,
      "limit": 200,
      "is_valid": false,
      "message": "Title exceeds limit by 20 chars (220/200)"
    }
  ]
}
```

---

## Pricing — /api/pricing

### POST /api/pricing/calculate

Calculate pricing for all marketplaces.

**Request Body** (`PricingRequest`)
```json
{
  "product_id": 5,
  "cost_price": 150.0,
  "weight_grams": 120.0,
  "category": "baseball_caps",
  "target_margin": 25.0,
  "shipping_zone": "national"
}
```

`shipping_zone` values: `local`, `regional`, `zonal`, `national`

When `product_id` is provided, calculates prices, saves snapshots, and updates the product
record with calculated prices and `listing_status = 'priced'`.

**Response `data`** (`PricingResponse`)
```json
{
  "amazon": {
    "selling_price": 285.0,
    "fees": {
      "referral_fee": 28.5,
      "closing_fee": 9.0,
      "shipping_fee": 57.0,
      "gst_on_fees": 17.0
    },
    "total_fees": 111.5,
    "profit": 23.5,
    "margin_percent": 8.25
  },
  "flipkart": {...},
  "meesho": {...}
}
```

---

### POST /api/pricing/calculate/batch

Calculate pricing for multiple products at once.

**Request Body** — array of `PricingRequest`

**Response `data`** — array of `PricingResponse`

---

### POST /api/pricing/auto-price/{product_id}

Auto-price a product by reading its cost and weight from the database.

**Path Parameters**: `product_id` (int)

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `target_margin` | float | 25.0 | Desired margin % |
| `shipping_zone` | string | `national` | Shipping zone |

Saves pricing snapshots and updates the product's price fields and `listing_status = 'priced'`.

**Errors**
- `404` — Product not found
- `400` — Product has no cost price set

---

### GET /api/pricing/fee-structure/{marketplace}

Return the full fee structure constants for a marketplace.

**Path Parameters**: `marketplace` — `amazon`, `flipkart`, or `meesho`

**Response `data`** — full fee structure dict from `config.py`

---

## Templates — /api/templates

### POST /api/templates/preview

Return export data as JSON for UI preview. Same data as the Excel export.

**Request Body** (`FullExportRequest`)
```json
{
  "product_ids": [1, 2, 3],
  "marketplace": "all"
}
```

`marketplace` values: `all`, `amazon`, `flipkart`, `meesho`

**Response `data`** — array of flat row dicts. Each row includes:
- `sku`, `name`, `brand`, `category`, `cost_price`, `weight_grams`, `listing_status`
- `is_variation` (bool) — whether this row is a variation row
- Marketplace-specific fields depending on the `marketplace` filter

---

### POST /api/templates/export

Generate and download an Excel file.

**Request Body** — same as `/preview`

**Response** — `FileResponse` (`.xlsx` binary)
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: `attachment; filename="..."`

Also creates an `export_history` record per product.

**Errors**
- `500` — Excel generation failed

---

### GET /api/templates/exports

List recent export history (last 50).

**Response `data`** — array of `ExportHistoryResponse`

---

### GET /api/templates/download/{filename}

Download a previously generated export file.

**Path Parameters**: `filename` — filename within the exports directory

Directory traversal is prevented by resolving the full path and checking it starts with
the configured `EXPORT_PATH`.

**Errors**
- `400` — Invalid filename (traversal attempt)
- `404` — File not found

---

## Vision — /api/vision

### POST /api/vision/detect

Upload a product image and detect attributes using Gemini Vision.

**Request** — `multipart/form-data`, field `file`

Accepted types: `image/jpeg`, `image/png`, `image/webp`  
Maximum size: 10 MB

**Response `data`** (`VisionDetectionResponse`)
```json
{
  "product_type": "baseball cap",
  "suggested_name": "Adjustable Cotton Baseball Cap",
  "category": "baseball_caps",
  "subcategory": "sports caps",
  "material": "cotton",
  "colors": ["black", "navy blue"],
  "key_features": ["adjustable strap", "breathable fabric"],
  "suggested_keywords": ["baseball cap", "cotton cap"],
  "confidence": 0.92,
  "suggested_weight_grams": 120,
  "suggested_hsn_code": "65050090"
}
```

Uploaded images are saved to `data/uploads/` for audit trail.

**Errors**
- `400` — Unsupported file type, oversized file, or Gemini API key missing
- `500` — Detection failed

---

## Settings — /api/settings

### GET /api/settings/

Get all app settings. Merges DB-stored values over `.env` defaults.

**Response `data`**
```json
{
  "gemini_api_key_configured": "true",
  "gemini_model": "gemini-2.5-flash",
  "default_margin": "25",
  "headless_browser": "True",
  "scraper_min_delay": "2",
  "scraper_max_delay": "4",
  "export_path": "data/exports",
  "upload_path": "data/uploads"
}
```

All values are strings.

---

### PUT /api/settings/{key}

Update a single setting. Upserts into `app_settings` table.

**Path Parameters**: `key` — setting key  
**Query Parameters**: `value` (string) — new value

```
PUT /api/settings/gemini_api_key?value=AIzaSy...
```

---

### GET /api/settings/{key}

Read a single setting.

**Errors**
- `404` — Setting not found in DB (falls back message only, does not expose `.env` values)

---

### POST /api/settings/test-gemini

Test a Gemini API key by sending a minimal prompt.

**Query Parameters**: `api_key` (string, optional) — key to test; falls back to `.env` key

**Response `data`**
```json
{"response": "OK"}
```

**Errors**
- `400` — No key available or key is invalid
