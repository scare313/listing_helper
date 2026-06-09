# Architecture

## High-Level System Architecture

Listing Helper is a single-host web application. There is no external database server, no
message queue, and no separate frontend build step. Everything runs in a single Python process.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (SPA)                           │
│   index.html + css/styles.css + js/app.js                       │
│   Vanilla JS — no framework, no build tool                      │
└────────────────────────┬────────────────────────────────────────┘
                         │  HTTP REST + SSE (Server-Sent Events)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI (main.py)                             │
│   Uvicorn ASGI server — async throughout                        │
│                                                                 │
│  Routers                    Modules (business logic)            │
│  ├── /api/products          ├── keyword_research.py             │
│  ├── /api/keywords ─SSE──►  ├── content_generator.py           │
│  ├── /api/content           ├── vision_detector.py              │
│  ├── /api/pricing           └── excel_exporter.py               │
│  ├── /api/templates                                             │
│  ├── /api/vision            External APIs                       │
│  └── /api/settings          ├── Google Gemini API               │
│                             └── Amazon autocomplete API         │
│  config.py                                                      │
│  ├── AppSettings (Pydantic dataclass, loaded from .env)         │
│  ├── Fee structure constants (AMAZON_FEES, FLIPKART_FEES, etc.) │
│  └── Marketplace limits (MARKETPLACE_LIMITS)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │  aiosqlite (async)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SQLite (data/listing_helper.db)                │
│   WAL mode, foreign keys ON                                     │
│   Tables: products, product_variations, variation_content,      │
│           keyword_researches, pricing_snapshots,                │
│           export_history, app_settings                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

The frontend is a hand-written Single-Page Application (SPA) with no framework, no bundler, and
no TypeScript. All code lives in `static/js/app.js` (~2500 lines).

### Navigation Model

Navigation is hash-based. `navigateTo(page)` switches between three top-level pages:
`dashboard`, `products`, `settings`. All other UI (wizard, product details) is rendered as
modal overlays on top of the current page.

Pages are defined by their render function:
- `renderDashboard()` — Kanban board
- `renderProducts()` — filterable product list
- `renderSettings()` — app configuration

Unknown page names redirect to `dashboard` (enforced whitelist in `navigateTo()`).

### Wizard Architecture

The Product Wizard is the primary interaction surface. It renders inside a fixed-position overlay
(`.wizard-overlay`) that sits above the page content. The wizard has 5 steps:

```
Step 1: Product Info   → saveWizardStep1()
Step 2: Keywords       → saveWizardStep2()
Step 3: Content        → saveWizardStep3()
Step 4: Pricing        → saveWizardStep4()
Step 5: Export         → finishWizard()
```

`goToWizardStep(n)` controls step transitions. Each step's save function calls the relevant API
and returns `true` to advance or `false` to block (e.g., validation failed).

### State Variables

All wizard state is module-level globals in `app.js`:

| Variable | Type | Purpose |
|---|---|---|
| `wizardStep` | `number` | Current active step (1–5) |
| `wizardProduct` | `object\|null` | Product being edited (DB row) |
| `wizardVariations` | `array` | Product variations loaded from DB |
| `wizardStep3ActiveTab` | `string` | `'base'` or variation ID |
| `wizardStep3Data` | `object` | In-memory content store `{base: {...}, variations: {}}` |
| `wizardPricingResult` | `object\|null` | Last pricing calculation result |
| `activePreviewMarketplace` | `string` | `'all'`, `'amazon'`, `'flipkart'`, `'meesho'` |

### API Communication

All HTTP requests go through the `api(path, method, body)` helper which:
1. Prepends `/api` to the path
2. Sends JSON
3. Returns the parsed `ApiResponse` object `{success, message, data}`
4. Throws on `success === false` or network error

Callers always access the payload via `res.data`.

---

## Backend Architecture

### Configuration (config.py)

`AppSettings` is a frozen dataclass (not Pydantic BaseSettings) loaded from `.env` at import
time via `python-dotenv`. It is instantiated once as the module-level `settings` singleton.

**Important**: `settings` is loaded at process startup and never reloaded. Settings saved through
the UI go to the `app_settings` DB table. Backend modules that need to respect UI-saved settings
must read from the DB via `get_setting(key)` and fall back to `settings.*`. This pattern is
implemented for `headless_browser`, `scraper_min_delay`, `scraper_max_delay`, and `gemini_api_key`.

`config.py` also contains all fee structure constants (`AMAZON_FEES`, `FLIPKART_FEES`,
`MEESHO_FEES`), category mappings (`CATEGORY_MAPPINGS`), and marketplace limits
(`MARKETPLACE_LIMITS`). These are used by both the pricing router and the content generator.

### Router Layer (routers/)

Each router is a `fastapi.APIRouter` registered in `main.py` with a URL prefix. Routers handle:
- Request validation (via Pydantic models)
- Calling DB functions or module functions
- Error mapping (DB 404 → HTTP 404, Gemini error → HTTP 502)
- Response wrapping in `ApiResponse`

Routers do not contain business logic. The one exception is `routers/pricing.py`, which currently
embeds the pricing calculation functions — a known architectural issue tracked as R-16.

### Module Layer (modules/)

Business logic lives in modules. Each module is independently importable.

| Module | Responsibility |
|---|---|
| `keyword_research.py` | Amazon scraping (dual strategy) + NLP analysis |
| `content_generator.py` | Gemini API calls, prompt building, retry logic |
| `vision_detector.py` | Gemini Vision API, image analysis |
| `excel_exporter.py` | openpyxl workbook generation |

### Database Layer (database.py)

All database access is async via `aiosqlite`. The `get_db()` async context manager creates a
fresh connection per call with `Row` factory (dict-like access) and WAL journal mode.

There is no ORM. Queries are raw SQL with parameterised placeholders.

JSON columns (`amazon_bullets`, `flipkart_key_features`, `keywords_data`, `competitor_data`,
`results`, `fees_breakdown`, `bullets`) are serialised/deserialised by `database.py` helpers.

---

## Request Flow

### Standard API Request

```
Browser
  │  POST /api/content/generate  {product_id, marketplace, keywords}
  ▼
main.py  (CORS middleware passes through)
  │
  ▼
routers/content.py :: generate_content()
  │  1. Validate Pydantic model
  │  2. get_product(product_id)  ──► database.py ──► SQLite
  │  3. generate_marketplace_content(...)
  │        │
  │        ▼
  │     modules/content_generator.py :: _call_gemini(prompt)
  │        │  Gemini API (google-genai SDK)
  │        ▼
  │     parse + validate response
  │  4. _save_content_to_product(...)  ──► database.py ──► SQLite
  │  5. Return ApiResponse
  ▼
Browser  {success: true, data: {amazon: {...}, flipkart: {...}, meesho: {...}}}
```

### SSE Keyword Research Flow

```
Browser
  │  GET /api/keywords/research/stream?seed=baseball+cap&limit=25
  ▼
routers/keywords.py :: keyword_research_stream()
  │  Creates asyncio.Queue
  │  Spawns asyncio.Task: run_scraper()
  │    │  scrape_keywords(seed, ..., progress_callback)
  │    │    ├── _scrape_fast_path_sync()  (in thread pool)
  │    │    │     ├── GET amazon.in/s?k=...
  │    │    │     └── GET /dp/ASIN × N  (random 2–4s delays)
  │    │    ├── [if blocked] _scrape_selenium_sync()  (in thread pool)
  │    │    ├── _analyze_nlp(titles, bullets, descriptions)
  │    │    ├── get_autocomplete_suggestions()
  │    │    └── puts "complete" event with results on queue
  │
  │  event_generator() reads from queue and yields SSE frames
  ▼
Browser  data: {"step": "scraping_product", "current": 3, "total": 25, ...}
         data: {"step": "complete", "results": {"primary": [...], ...}}
```

---

## Keyword Research Workflow

### Dual-Strategy Scraping

```
seed (keyword or Amazon URL)
    │
    ▼
Strategy 1: requests + BeautifulSoup
    ├── GET listing/search page with random User-Agent
    ├── Extract /dp/ASIN links (de-duplicate by ASIN)
    ├── GET each product page (2–4s random delay)
    │   └── Parse title (#productTitle), bullets (#feature-bullets),
    │       description (#productDescription or #aplus)
    │
    └── [if blocked → 503/429/CAPTCHA detected]
         ▼
        Strategy 2: Selenium headless Chrome
            ├── Stealth flags: --disable-blink-features=AutomationControlled
            ├── Remove navigator.webdriver via CDP
            └── Same scraping flow with real browser rendering
    │
    └── [if both strategies return no titles]
         ▼
        Local Fallback: _run_local_fallback(seed)
            └── Returns keyword templates based on seed word
                (zero real data, always works)
    │
    ▼
NLP Analysis (_analyze_nlp)
    ├── Unigram frequency (titles weighted 3×)
    ├── Bigrams, trigrams, 4-grams
    ├── Co-occurrence pairs
    └── Stopword filtering
    │
    ▼
Keyword Categorisation (_build_results)
    ├── primary[]   — top bigrams (up to 12)
    ├── secondary[] — top trigrams (up to 15)
    ├── long_tail[] — top 4-grams (up to 10)
    └── trending[]  — unigram + co-occurrence derived (up to 10)
    │
    ▼
Amazon Autocomplete
    └── GET https://completion.amazon.in/api/2017/suggestions?prefix=...
    │
    ▼
save_keyword_research(seed, results, product_id)  ──► SQLite
```

---

## Pricing Workflow

All pricing logic lives in `routers/pricing.py` (tracked for extraction to `modules/pricing_engine.py`).

```
Input: cost_price, weight_grams, category, target_margin, shipping_zone
    │
    ▼
_calculate_target_price(marketplace, ...)
    │  Iterative approximation (up to 20 iterations, converges to ±0.1% margin)
    │  Starting estimate: cost / (1 - margin/100) × 1.3
    │  Adjusts: price += (needed_profit - actual_profit) × 0.8
    ▼
target_price per marketplace
    │
    ▼
_calculate_marketplace_pricing(marketplace, cost, price, weight, category, zone)
    ├── get_referral_fee_rate()  ← config.py
    ├── get_closing_fee()        ← config.py
    ├── get_shipping_fee()       ← config.py
    ├── [Flipkart only] collection_fee = max(5, min(price × 2%, 25))
    ├── gst_on_fees = subtotal × 18%
    └── profit = price - cost - total_fees
    │
    ▼
MarketplacePricing {selling_price, fees{}, total_fees, profit, margin_percent}
    │
    ├── [if product_id] save_pricing_snapshot()  ──► SQLite
    ├── [if product_id] update_product(prices, listing_status='priced')
    └── Return PricingResponse {amazon, flipkart, meesho}
```

---

## Export Workflow

```
POST /api/templates/export  {product_ids: [1, 2, 3], marketplace: "all"}
    │
    ▼
templates.py :: export_template()
    ├── _load_products_and_variations(product_ids)
    │     └── get_product(id) + get_all_variation_content_for_product(id)
    │
    ▼
modules/excel_exporter.py :: generate_export_excel(products, variations_map, filename)
    │
    ├── Sheet 1: "All Products" (_create_all_products_sheet)
    │     Headers: SKU, Name, Brand, Category, Cost, Weight, Status,
    │              Amazon Title, Bullet 1–5, Description, Search Terms, Price,
    │              Flipkart Title, Feature 1–6, Description, Keywords, Price,
    │              Meesho Title, Description, Price
    │
    ├── Sheet 2: "Amazon" (_create_marketplace_sheet)
    │     Headers: SKU, Title, Brand, Bullet 1–5, Description, Search Terms, Price, Category
    │
    ├── Sheet 3: "Flipkart"
    │     Headers: SKU, Title, Brand, Feature 1–6, Description, Keywords, Price, Category
    │
    └── Sheet 4: "Meesho"
          Headers: SKU, Title, Brand, Description, Price, Category
    │
    ├── [For each product] append variation rows beneath parent row
    ├── Auto-fit column widths (capped at 50 chars)
    └── Style: marketplace-coloured header fills, white text, borders
    │
    ▼
Save to data/exports/{marketplace}_listing_export_{timestamp}.xlsx
    │
    ├── create_export_record()  ──► export_history table
    └── Return FileResponse (browser download)
```
