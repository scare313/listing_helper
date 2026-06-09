# Configuration

Listing Helper uses a two-tier configuration system:

1. **`.env` file** — loaded at startup into the frozen `AppSettings` dataclass. Changes
   require a server restart.
2. **`app_settings` database table** — read at call time by backend modules. Changes take
   effect immediately without restart.

Only the four settings listed below support DB override. Everything else is `.env` only.

---

## .env Reference

Copy `.env.example` to `.env` before first run. Only `GEMINI_API_KEY` is required;
all other settings have working defaults.

### API Keys

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | **Yes** | `""` | Google Gemini API key. Obtain at https://aistudio.google.com/. Free tier: 15 requests/minute, 1M tokens/day. |

### App Settings

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_HOST` | No | `127.0.0.1` | Host to bind. Use `0.0.0.0` to expose on local network. |
| `APP_PORT` | No | `8000` | Port to listen on. |
| `DATABASE_PATH` | No | `data/listing_helper.db` | Path to SQLite file. Created automatically. |
| `EXPORT_PATH` | No | `data/exports` | Directory for generated Excel files. Created automatically. |
| `UPLOAD_PATH` | No | `data/uploads` | Directory for uploaded product images. Created automatically. |
| `DEFAULT_TARGET_MARGIN` | No | `25` | Default margin percentage for pricing calculations. |

### Scraper Settings

| Variable | Required | Default | Description |
|---|---|---|---|
| `HEADLESS_BROWSER` | No | `True` | Run Selenium Chrome in headless mode. Set to `False` to see the browser window (useful for debugging). |
| `SCRAPER_MIN_DELAY` | No | `2` | Minimum seconds between product page requests. |
| `SCRAPER_MAX_DELAY` | No | `4` | Maximum seconds between product page requests. Actual delay is `random.uniform(min, max)`. |
| `SCRAPER_MAX_RETRIES` | No | `2` | Maximum retry attempts per failed request in the fast-path scraper. |

### Reserved (Future SP-API Integration)

These are defined in `.env.example` but not currently used by any code:

| Variable | Description |
|---|---|
| `AMAZON_SP_API_REFRESH_TOKEN` | Amazon Selling Partner API OAuth refresh token |
| `AMAZON_SP_API_CLIENT_ID` | SP-API client ID |
| `AMAZON_SP_API_CLIENT_SECRET` | SP-API client secret |
| `AMAZON_MARKETPLACE_ID` | Amazon India marketplace ID (`A21TJRUUN4KGV`) |
| `FLIPKART_APP_ID` | Flipkart API app ID |
| `FLIPKART_APP_SECRET` | Flipkart API secret |

---

## Database Settings (app_settings table)

These settings are written by the Settings UI and override `.env` values at call time.
Read via `await get_setting(key)` in `database.py`.

| Key | Type | Description | Falls back to |
|---|---|---|---|
| `gemini_api_key` | string | Gemini API key override | `settings.GEMINI_API_KEY` |
| `headless_browser` | string `"True"/"False"` | Selenium headless mode | `settings.HEADLESS_BROWSER` |
| `scraper_min_delay` | string (float) | Min scraper delay seconds | `settings.SCRAPER_MIN_DELAY` |
| `scraper_max_delay` | string (float) | Max scraper delay seconds | `settings.SCRAPER_MAX_DELAY` |

All values are stored as strings. Backend code casts them before use:
```python
db_min = await get_setting("scraper_min_delay")
resolved_min = float(db_min) if db_min is not None else settings.SCRAPER_MIN_DELAY
```

Additional keys that the settings router writes but are not read by backend modules:
- `gemini_model` — informational only (model is hardcoded as `gemini-2.5-flash` in code)
- `default_margin` — read by frontend only (UI pre-fills the margin slider)
- `export_path`, `upload_path` — informational only

---

## Fee Structure Constants (config.py)

These are hardcoded in `config.py`. They are not configurable via `.env` or the Settings UI.
To change fee structures, edit `config.py` and restart the server.

### Amazon Fee Slabs

```python
AMAZON_FEES = {
    "referral_rates": {
        "sports_and_fitness": [
            {"max_price": 250, "rate": 0.05},
            {"max_price": 500, "rate": 0.08},
            {"max_price": float("inf"), "rate": 0.10},
        ],
        # ... other categories
    },
    "closing_fees": [
        {"max_price": 250, "fee": 4},
        {"max_price": 500, "fee": 9},
        # ...
    ],
    "shipping_fees": {
        "local":    {"0-500g": 29, "500g-1kg": 49, ...},
        "regional": {"0-500g": 43, ...},
        "zonal":    {"0-500g": 51, ...},
        "national": {"0-500g": 57, ...},
    }
}
```

### Flipkart Fee Slabs

```python
FLIPKART_FEES = {
    "commission_rates": {
        "sports": [
            {"max_price": 250, "rate": 0.06},
            {"max_price": 500, "rate": 0.08},
            {"max_price": float("inf"), "rate": 0.10},
        ],
        # ...
    },
    "fixed_fees": [...],
    "shipping_fees": { ... }
}
```

### Meesho Fee Structure

```python
MEESHO_FEES = {
    "commission_rate": 0.0,
    "shipping_fees": {
        "local":    {"0-500g": 30, ...},
        "national": {"0-500g": 65, ...},
    }
}
```

All fees are in INR. GST (18%) is applied on top of all marketplace fees automatically
in the pricing calculation.

---

## Marketplace Limits (config.py)

```python
MARKETPLACE_LIMITS = {
    "amazon": {
        "title": 200,
        "bullet": 500,
        "bullet_count": 5,
        "description": 2000,
        "search_terms": 250,
    },
    "flipkart": {
        "title": 500,
        "feature": 200,
        "feature_count": 10,
        "description": 5000,
        "keywords": 500,
    },
    "meesho": {
        "title": 200,
        "description": 2000,
    }
}
```

These are used by:
- `content_generator.py` — embedded in prompts
- `routers/content.py` — validation endpoint

---

## Recommended Values

| Setting | Recommended | Rationale |
|---|---|---|
| `SCRAPER_MIN_DELAY` | `2` | Minimum safe delay to avoid 429 responses |
| `SCRAPER_MAX_DELAY` | `5` | Higher values reduce risk of IP-level throttling |
| `HEADLESS_BROWSER` | `True` | Only set to `False` when debugging scraper |
| `DEFAULT_TARGET_MARGIN` | `25–30` | Leaves room for discounts and fee increases |
| `SCRAPER_MAX_RETRIES` | `2` | More retries rarely help; fall through to Selenium instead |

---

## Category Keys

The `category` field in products uses these internal keys:

| Key | Display Name |
|---|---|
| `baseball_caps` | Baseball Caps |
| `home_kitchen` | Home & Kitchen |
| `sports_fitness` | Sports & Fitness |
| `electronics` | Electronics |
| `clothing` | Clothing & Apparel |
| `accessories` | Accessories |

These are defined in `config.py :: CATEGORY_MAPPINGS` and must match the `category`
field values stored in the `products` table.
