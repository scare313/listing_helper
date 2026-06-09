# Changelog

---

## v2.0 — Current

_Phase 1 through Phase 4 completed. Major redesign from 7 disconnected pages to a
5-step wizard with full feature set._

### New Features

**Phase 1 — Keyword Research**
- Dual-strategy Amazon scraper: requests + BeautifulSoup (fast path) → Selenium headless
  Chrome (fallback)
- Real-time SSE progress streaming during keyword research
- NLP analysis: unigram frequency (titles weighted 3×), bigrams, trigrams, 4-grams,
  co-occurrence pairs, stopword filtering
- Amazon autocomplete API integration
- Local fallback when both scraping strategies fail
- Keyword research results cached in `keyword_researches` table
- `product_id` link added to `keyword_researches` (migration applied automatically)
- Keyword selection UI: pills with checkboxes, secondary keyword lists

**Phase 2 — AI Content Generation**
- Gemini 2.5 Flash content generation for Amazon, Flipkart, and Meesho
- Variation-aware generation: base product content + per-variant adapted content
- `variation_content` table (new in v2.0)
- Exponential backoff retry (5 attempts: 1, 2, 4, 8, 16 seconds) on 429/503
- `response_mime_type="application/json"` for structured Gemini output
- Content validation endpoint: checks character limits per marketplace
- Inline content editing with live character counters in the wizard

**Phase 3 — Image-Based Product Detection**
- `modules/vision_detector.py` (new) — Gemini Vision API
- `routers/vision.py` (new) — multipart image upload endpoint
- Returns: product_type, suggested_name, category, material, colors, key_features,
  suggested_keywords, confidence, suggested_weight_grams, suggested_hsn_code
- Uploaded images saved to `data/uploads/` for audit trail

**Phase 4 — Export & Pricing**
- `modules/excel_exporter.py` (new) — real 4-sheet openpyxl workbook
- Sheet structure: All Products, Amazon, Flipkart, Meesho
- Variation rows appended beneath parent product rows
- Marketplace-coloured header fills (navy, orange, blue, purple)
- Auto-fit column widths (capped at 50 chars)
- Iterative pricing approximation: converges to ±0.1% of target margin within 20 iterations
- `/api/pricing/auto-price/{product_id}` endpoint
- `/api/pricing/calculate/batch` endpoint
- Export history tracked in `export_history` table
- `routers/settings.py` (new) — API key and scraper config management
- `app_settings` table (new) — runtime configuration overrides

**Wizard UI Overhaul**
- Replaced 7 disconnected pages with a 5-step guided wizard
- Step 1: Product form + image drag-and-drop
- Step 2: Keyword research with SSE progress bar
- Step 3: Three-column content editor (Amazon / Flipkart / Meesho) with variation tabs
- Step 4: Pricing calculator with fee breakdown and margin slider
- Step 5: Export preview table + marketplace filter tabs + Excel download
- Dashboard Kanban board: 6 columns (new / keywords_done / content_ready / priced / exported / listed)

### Bug Fixes (post-v2.0)

- **SSE double `complete` event**: Internal fallback/exception paths emitted `step: "complete"`
  before the router could emit the final event with the results payload. Fixed by using
  `step: "fallback"` and `step: "error"` for internal paths. The router is now the sole
  emitter of `step: "complete"`.

- **Frontend crash on missing results payload**: `renderWizardKeywordResults(undefined)` 
  would throw `TypeError: Cannot read properties of undefined (reading 'primary')`. Added
  null-guard at function entry.

- **Null guard in SSE `onmessage`**: Added check for `data.results` on `complete` events
  before calling `renderWizardKeywordResults`.

- **Scraper delays ignoring Settings UI**: `_scrape_fast_path_sync` and `_scrape_selenium_sync`
  were reading delay values from `settings.*` (fixed at startup) instead of from the DB.
  Fixed by resolving delay values via `get_setting()` in `scrape_keywords()` and passing
  them as parameters to the sync functions.

### Database Migrations Applied

The following `ALTER TABLE` migrations are applied automatically at startup to existing
v1.x databases:
```sql
ALTER TABLE products ADD COLUMN listing_status TEXT DEFAULT 'new'
ALTER TABLE keyword_researches ADD COLUMN product_id INTEGER REFERENCES products(id)
```

---

## v1.x — Initial Implementation

_No formal version history was maintained. The following is reconstructed from the
database schema and codebase._

- Basic product CRUD (`products` table)
- `product_variations` table
- `keyword_researches` table (no `product_id` link)
- `pricing_snapshots` table
- `export_history` table
- Basic pricing calculation (static fee structure)
- Gemini content generation (mock fallback present in earlier versions)
- 7-page UI (no wizard)
- Basic Excel export (stub or simple single-sheet)
