# Backend

The backend is a Python 3.x FastAPI application running on Uvicorn. It is fully async
throughout. All database access uses `aiosqlite`. Blocking operations (scraping, Selenium)
are offloaded to the thread pool via `asyncio.to_thread`.

---

## Entry Point (main.py)

```python
app = FastAPI(title="Listing Helper", version="1.0.0")

@asynccontextmanager
async def lifespan(app):
    os.makedirs(settings.EXPORT_PATH, exist_ok=True)
    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
    await init_db()
    yield

app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.get("/", ...) -> FileResponse("static/index.html")
```

All 7 routers are registered at startup with their URL prefixes. The lifespan handler
creates the exports and uploads directories and initialises the database schema.

**Note**: The app version string in the startup log is `"1.0.0"`, but the documentation
refers to `v2.0`. This discrepancy should be resolved (see KNOWN_LIMITATIONS.md).

---

## Configuration Layer (config.py)

`AppSettings` is a `@dataclass(frozen=True)` — not Pydantic BaseSettings. It is loaded
once at import time via `python-dotenv`:

```python
@dataclass(frozen=True)
class AppSettings:
    GEMINI_API_KEY: str = ""
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DATABASE_PATH: str = "data/listing_helper.db"
    EXPORT_PATH: str = "data/exports"
    UPLOAD_PATH: str = "data/uploads"
    DEFAULT_TARGET_MARGIN: float = 25.0
    HEADLESS_BROWSER: bool = True
    SCRAPER_MIN_DELAY: float = 2.0
    SCRAPER_MAX_DELAY: float = 4.0
    SCRAPER_MAX_RETRIES: int = 2

settings = AppSettings(...)  # module-level singleton
```

Because the dataclass is frozen, settings cannot be changed at runtime. The UI settings
page writes overrides to the `app_settings` database table, and backend modules read from
the DB at call time (using `get_setting(key)`) with `.env` values as fallback.

`config.py` also contains all fee structure constants:
- `AMAZON_FEES` — referral rates, closing fees, shipping fees by slab/weight/zone
- `FLIPKART_FEES` — commission rates, fixed fees, shipping fees
- `MEESHO_FEES` — shipping fees (0% commission)
- `CATEGORY_MAPPINGS` — human-readable → marketplace category codes
- `MARKETPLACE_LIMITS` — title/description/bullet character limits per marketplace
- `SCRAPER_USER_AGENTS` — 10 rotating User-Agent strings

Helper functions exported by `config.py`:
- `get_referral_fee_rate(marketplace, category, price)` → float
- `get_closing_fee(marketplace, price)` → float
- `get_shipping_fee(marketplace, weight_grams, zone)` → float

---

## Router Layer (routers/)

Each router is a `fastapi.APIRouter`. Routers handle request validation, call the
database or module functions, map errors to HTTP status codes, and wrap responses in
`ApiResponse`.

```
/api/products  → routers/products.py
/api/keywords  → routers/keywords.py
/api/content   → routers/content.py
/api/pricing   → routers/pricing.py
/api/templates → routers/templates.py
/api/vision    → routers/vision.py
/api/settings  → routers/settings.py
```

### routers/products.py

CRUD for products and variations. Key operations:
- `GET /` — list with pagination and filters; uses `LIKE` for search
- `POST /` — create product; returns 409 on duplicate SKU
- `PUT /{id}` — partial update; only fields in request body are modified
- `DELETE /{id}` — cascades to variations via FK
- `GET /{id}/variations` — list variations
- `POST /{id}/variations` — add variation
- `DELETE /{id}/variations/{vid}` — remove variation
- `GET /{id}/variation-content` — all variation content (joined with variations table)
- `PUT /{id}/variation-content` — bulk upsert variation content

### routers/keywords.py

Keyword research endpoints:
- `POST /research` — non-streaming; checks cache first
- `GET /research/stream` — SSE streaming endpoint (see SSE section below)
- `GET /autocomplete` — Amazon autocomplete API proxy
- `GET /history` — recent research records
- `POST /apply-to-product` — save selected keywords to product

### routers/content.py

AI content generation:
- `POST /generate` — single product, one or all marketplaces
- `POST /generate/all` — alias for generate with `marketplace='all'`
- `POST /generate-with-variations` — base product + all variations
- `POST /validate` — validate content lengths against marketplace limits

### routers/pricing.py

Pricing calculation. **Note**: Business logic is embedded here instead of in a module
(tracked as architectural debt R-16, should be extracted to `modules/pricing_engine.py`).

- `POST /calculate` — full pricing for all marketplaces
- `POST /calculate/batch` — array input, array output
- `POST /auto-price/{id}` — reads product from DB, calculates, saves
- `GET /fee-structure/{marketplace}` — expose fee constants for UI

### routers/templates.py

Export preview and download:
- `POST /preview` — return JSON rows for UI table
- `POST /export` — generate Excel, return as FileResponse
- `GET /exports` — list export history
- `GET /download/{filename}` — serve previously generated file

### routers/vision.py

Image-based product detection:
- `POST /detect` — multipart upload, calls Gemini Vision, returns detection result
- Validates MIME type and file size before calling Gemini
- Saves uploaded image to `data/uploads/` for audit trail

### routers/settings.py

App configuration management:
- `GET /` — merged view of all settings (DB over `.env`)
- `PUT /{key}` — upsert a setting to the DB
- `GET /{key}` — read a single setting from DB
- `POST /test-gemini` — validate API key with a minimal prompt

---

## Module Layer (modules/)

### modules/keyword_research.py

**Responsibilities**: Amazon scraping with dual strategy, NLP analysis, SSE progress reporting.

#### Scraping Strategies

**Strategy 1 — requests + BeautifulSoup** (`_scrape_fast_path_sync`):
```python
def _scrape_fast_path_sync(seed, limit, progress_cb, min_delay, max_delay):
    headers = {"User-Agent": random.choice(SCRAPER_USER_AGENTS)}
    # Step 1: GET search/bestseller page, extract /dp/ ASIN links
    # Step 2: GET each product page with random delay
    #   Parse: #productTitle, #feature-bullets, #productDescription or #aplus
    # Return: list of {title, bullets, description}
```

Called via `asyncio.to_thread` to avoid blocking the event loop.

**Strategy 2 — Selenium headless Chrome** (`_scrape_selenium_sync`):
```python
def _scrape_selenium_sync(seed, limit, progress_cb, headless, min_delay, max_delay):
    opts = ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    # Same scraping flow but with real browser rendering
```

Only invoked when Strategy 1 is blocked (no titles returned, or HTTP 503/429).

**Local fallback** (`_run_local_fallback`):
Returns template keywords derived from the seed word. Always succeeds. Used when both
scraping strategies fail. Emits a `fallback` SSE step (not `complete`) to signal degraded mode.

#### SSE Progress Reporting

The `scrape_keywords()` async function accepts a `progress_callback` coroutine. The callback
puts a dict onto an `asyncio.Queue`. The router's `event_generator()` reads from the queue
and yields SSE frames. The queue uses sentinel `None` to signal stream end.

Step values emitted:
- `collecting_links` — finding product URLs
- `scraping_product` — scraping each product page (one event per product)
- `analyzing` — NLP analysis running
- `autocomplete` — fetching Amazon autocomplete
- `fallback` — scraping failed, using local fallback
- `complete` — all done; `results` payload attached
- `error` — unrecoverable exception

**Important**: Only the router emits `step: "complete"`. Internal fallback/exception paths
emit `step: "fallback"` or `step: "error"`. This prevents duplicate `complete` events
from reaching the browser.

#### NLP Analysis (`_analyze_nlp`)

```python
def _analyze_nlp(titles, bullets, descriptions):
    # 1. Tokenise all text (lowercase, strip punctuation)
    # 2. Unigram frequency: title tokens weighted 3×, others 1×
    # 3. Build bigrams, trigrams, 4-grams from each document
    # 4. Frequency sort all n-gram lists
    # 5. Co-occurrence pairs: any two words appearing in the same document
    # 6. Filter: remove stopwords + generic e-commerce terms
    # Return: {primary, secondary, long_tail, trending, metrics}
```

Stopwords include common English words plus e-commerce-specific terms like "buy", "online",
"free", "shipping", "india".

#### Scraper Delay Settings

Both sync scraper functions accept `min_delay` and `max_delay` parameters (not globals).
`scrape_keywords()` resolves delays at call time:
```python
db_min = await get_setting("scraper_min_delay")
db_max = await get_setting("scraper_max_delay")
resolved_min = float(db_min) if db_min is not None else settings.SCRAPER_MIN_DELAY
resolved_max = float(db_max) if db_max is not None else settings.SCRAPER_MAX_DELAY
```
This ensures Settings UI changes take effect without a server restart.

---

### modules/content_generator.py

**Responsibilities**: Build Gemini prompts, call the API, retry on rate limits, save content.

#### Prompt Building

`_build_marketplace_prompt(product, marketplace, keywords, variation_info)`:
- Injects product specs (name, brand, category, material, dimensions, HSN, notes)
- Injects top 15 keywords from the `keywords` parameter
- Adds marketplace-specific instructions (character limits, formatting rules)
- For variations: calls `_format_variation_instruction(variation_info)` to inject
  "This is for the {color} variant — adapt the title and first bullet accordingly"

Expected JSON response schema is embedded in the prompt using the marketplace's
field names and example values.

#### Gemini API Call (`_call_gemini`)

```python
async def _call_gemini(prompt, api_key=None):
    key = api_key or await get_setting("gemini_api_key") or settings.GEMINI_API_KEY
    client = genai.Client(api_key=key)
    
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except (ResourceExhausted, ServiceUnavailable) as e:
            if attempt == 4: raise
            await asyncio.sleep(2 ** attempt)  # 1, 2, 4, 8, 16 seconds
```

`response_mime_type="application/json"` is set so Gemini constrains its output to valid
JSON. This avoids the need to strip markdown code fences.

#### Content Saving

After generation, `_save_content_to_product()` calls `update_product()` with the new
content fields and sets `amazon_status`, `flipkart_status`, `meesho_status` to `'ready'`
and `listing_status` to `'content_ready'`.

---

### modules/vision_detector.py

**Responsibilities**: Receive image bytes, call Gemini Vision, return structured detection result.

```python
async def detect_product(image_bytes, mime_type, api_key=None):
    key = api_key or await get_setting("gemini_api_key") or settings.GEMINI_API_KEY
    client = genai.Client(api_key=key)
    
    image_part = Part.from_bytes(data=image_bytes, mime_type=mime_type)
    prompt = """Analyze this product image. Return JSON:
    {
      "product_type": "...",
      "suggested_name": "...",
      ...
      "confidence": 0.92
    }"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[image_part, prompt],
        config=GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)
```

Uploaded images are saved to `settings.UPLOAD_PATH` before calling Gemini to provide
an audit trail independent of Gemini's storage.

---

### modules/excel_exporter.py

**Responsibilities**: Build a 4-sheet openpyxl workbook from product and variation data.

```python
def generate_export_excel(products, variations_map, filename):
    wb = openpyxl.Workbook()
    
    _create_all_products_sheet(wb, products, variations_map)
    _create_marketplace_sheet(wb, 'Amazon', AMAZON_COLS, products, variations_map)
    _create_marketplace_sheet(wb, 'Flipkart', FLIPKART_COLS, products, variations_map)
    _create_marketplace_sheet(wb, 'Meesho', MEESHO_COLS, products, variations_map)
    
    wb.save(filename)
```

Each sheet writer:
1. Writes a header row with marketplace-coloured fill and white bold text
2. Iterates products; writes one data row per product
3. For each product, checks `variations_map[product_id]`; writes variation rows indented
   below the parent (using variation-specific content from `variation_content` table)
4. Auto-fits column widths (capped at 50 characters to prevent unusably wide columns)

---

## Database Layer (database.py)

All access is async. `get_db()` returns an `aiosqlite.Connection` context manager:

```python
@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
```

Each CRUD function opens its own connection. There is no connection pool — SQLite in WAL
mode handles concurrent readers well enough for the expected load (~1 concurrent user).

### Helper: `_row_to_dict`

Converts `aiosqlite.Row` to a plain dict and auto-parses known JSON columns:
```python
JSON_COLUMNS = {
    'amazon_bullets', 'flipkart_key_features', 'keywords_data',
    'competitor_data', 'results', 'fees_breakdown', 'bullets'
}

def _row_to_dict(row):
    d = dict(row)
    for k, v in d.items():
        if k in JSON_COLUMNS and isinstance(v, str):
            d[k] = _parse_json_field(v)
    return d
```

### CRUD Functions by Table

| Function | Table | Notes |
|---|---|---|
| `create_product`, `get_product`, `update_product`, `delete_product`, `list_products` | products | `update_product` uses dynamic SQL to update only provided fields |
| `create_variation`, `get_variations`, `delete_variation` | product_variations | |
| `save_variation_content`, `get_variation_content`, `get_all_variation_content_for_product` | variation_content | Upsert on `(variation_id, marketplace)` |
| `save_keyword_research`, `get_keyword_research`, `get_keyword_research_history` | keyword_researches | Cache lookup by `(seed_keyword, product_id)` |
| `save_pricing_snapshot`, `get_pricing_snapshots` | pricing_snapshots | |
| `create_export_record`, `get_export_history` | export_history | |
| `get_setting`, `set_setting`, `get_all_settings` | app_settings | `get_setting` returns `None` if key not in DB |

---

## Error Handling

All routers return `ApiResponse` on both success and failure. HTTP status codes:

| Situation | HTTP Status |
|---|---|
| Success | 200 (or 201 for creates) |
| Product/resource not found | 404 |
| Duplicate SKU | 409 |
| Invalid input | 422 (FastAPI auto) |
| Gemini API key missing | 400 |
| Gemini API call failed | 502 |
| File not found (exports) | 404 |
| Directory traversal attempt | 400 |
| Internal server error | 500 |

FastAPI's default 422 Unprocessable Entity is returned by Pydantic validation before
the router function body is reached.

---

## Known Technical Debt

| ID | Issue | Location |
|---|---|---|
| R-16 | Pricing business logic in router instead of `modules/pricing_engine.py` | `routers/pricing.py` |
| — | `app` version string is `"1.0.0"` in `main.py` but v2.0 in docs | `main.py` line ~10 |
| — | No request logging middleware | `main.py` |
| — | CORS `allow_origins=["*"]` — acceptable for local tool, dangerous in production | `main.py` |
| — | No rate limiting on Gemini endpoints | `routers/content.py`, `routers/vision.py` |
| — | `competitor_data` column defined but never written | `database.py`, `models.py` |
