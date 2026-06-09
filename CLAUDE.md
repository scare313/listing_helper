# CLAUDE.md — Listing Helper Project Documentation

> **Last Updated**: 2026-06-08
> **Version**: v2.0 (Redesign)
> **Status**: Planning → Implementation

---

## Project Overview

**Listing Helper** is a local web application that automates the tedious process of creating product listings for Indian e-commerce marketplaces: **Amazon India**, **Flipkart**, and **Meesho**.

### Problem Statement

A seller creating 100 product listings per month spends ~200 hours/month on:
1. Researching keywords by browsing competitor listings manually
2. Writing marketplace-specific titles, descriptions, bullet points
3. Filling marketplace Excel templates column by column
4. Calculating pricing (fees + margin) for each marketplace
5. Tracking which listings are done and which are pending

### Solution

A wizard-driven web app that reduces the per-product listing time from ~2 hours to ~10 minutes:
- **Keyword Research**: Auto-scrapes Amazon bestseller/search pages, runs NLP analysis
- **AI Content Generation**: Gemini API generates marketplace-compliant copy
- **Image Detection**: Upload a product photo → auto-detect product type and attributes
- **Pricing Calculator**: Auto-calculates selling prices based on fees + target margin
- **Excel Export**: Preview in UI + one-click download of marketplace-ready spreadsheets

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.x + FastAPI + Uvicorn |
| Database | SQLite (via aiosqlite) |
| Frontend | Vanilla HTML/CSS/JS (SPA, no framework) |
| AI | Google Gemini API (2.5 Flash) — content generation + vision |
| Scraping | requests + BeautifulSoup (primary), Selenium (fallback) |
| Excel | openpyxl + xlsxwriter |
| Styling | Glassmorphism dark theme, Inter font |

---

## Architecture

```
c:\Automation\listing_helper\
├── CLAUDE.md                          # This file
├── .env                               # Environment config (API keys, settings)
├── .env.example                       # Template for .env
├── requirements.txt                   # Python dependencies
├── main.py                            # FastAPI app entry point
├── config.py                          # App settings, fee structures, constants
├── database.py                        # SQLite schema + CRUD functions
├── models.py                          # Pydantic request/response models
│
├── modules/                           # Business logic
│   ├── __init__.py
│   ├── keyword_research.py            # Scraping + NLP analysis
│   ├── content_generator.py           # Gemini AI content generation
│   ├── vision_detector.py             # [NEW] Gemini Vision product detection
│   └── excel_exporter.py              # [NEW] Real Excel file generation
│
├── routers/                           # API endpoints
│   ├── __init__.py
│   ├── products.py                    # Product CRUD
│   ├── keywords.py                    # Keyword research + SSE
│   ├── content.py                     # Content generation
│   ├── pricing.py                     # Fee calculation
│   ├── templates.py                   # Export preview + download
│   ├── vision.py                      # [NEW] Image detection
│   └── settings.py                    # [NEW] App configuration
│
├── static/                            # Frontend
│   ├── index.html                     # Main HTML (wizard + dashboard)
│   ├── css/styles.css                 # Glassmorphism dark theme
│   └── js/app.js                      # SPA logic (1500+ lines)
│
├── data/                              # Runtime data
│   ├── listing_helper.db              # SQLite database
│   └── exports/                       # Generated Excel files
│
└── .venv/                             # Python virtual environment
```

---

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| AI Provider | Gemini API (free tier) | 15 RPM free, same key for content + vision |
| Local LLM | Deferred | User's PC not powerful enough |
| Scraping Approach | requests+BS4 primary, Selenium fallback | Faster, less resource-heavy |
| Scraping Risk | Low | Public pages, no login, dynamic IP, human-like delays |
| Export Strategy | UI preview first, Excel download second | Reduces iteration cycles |
| Variation Handling | 1 row per variation in Excel | Color/size variants get tailored content |
| UI Pattern | Product Workflow Wizard | Single guided flow beats 7 disconnected pages |
| Database | SQLite | Simple, no setup, sufficient for 100 products/month |

---

## Product Categories

Currently handling:
- **Baseball Caps** (Sports & Fitness category)
- **Home & Kitchen Products** (multiple subcategories)

---

## Marketplace Fee Structures

### Amazon India
- Referral fee: 5-15% depending on category and price slab
- Closing fee: ₹4-61 based on price slab
- Weight handling: ₹29-140 based on weight and zone
- 18% GST on all marketplace fees

### Flipkart
- Commission: 6-16% depending on category and price slab
- Fixed fee: ₹6-40 based on price slab
- Shipping: ₹29-165 based on weight and zone
- Collection fee: 2% (min ₹5, max ₹25)
- 18% GST on all fees

### Meesho
- Commission: 0% (Meesho's USP)
- Shipping: ₹30-170 based on weight and zone
- 18% GST on shipping only

---

## Marketplace Content Limits

| Field | Amazon | Flipkart | Meesho |
|-------|--------|----------|--------|
| Title | 200 chars | 500 chars | 200 chars |
| Bullets/Features | 5 × 500 chars | 10 × 200 chars | N/A |
| Description | 2000 chars | 5000 chars | 2000 chars |
| Search Terms | 250 bytes | 500 chars | N/A (embed in description) |

---

## Implementation Phases (Priority Order)

### Phase 1: Keyword Research (Priority D — Most Time Saved)
**Goal**: Replace manual Amazon browsing with automated scraping + NLP

**Changes**:
- `config.py` — Add scraper delay settings, user agent rotation
- `modules/keyword_research.py` — Dual strategy (requests+BS4 → Selenium fallback), SSE progress, Amazon autocomplete API
- `routers/keywords.py` — SSE streaming endpoint, product linking, force refresh
- `database.py` — Link keyword_researches to product_id
- `main.py` — Register new endpoints

**Scraping Strategy**:
```
1. Fast Path (requests + BeautifulSoup):
   - GET bestseller page with random User-Agent
   - Parse product links from HTML
   - GET each product page (2-4s random delay between)
   - Parse title/bullets/description via CSS selectors
   
2. Fallback (Selenium — only if Fast Path fails):
   - Launch headless Chrome with stealth flags
   - Same scraping flow but with real browser rendering
   
3. Amazon Autocomplete (bonus):
   - GET https://completion.amazon.in/api/2017/suggestions?prefix=...
   - Returns real search suggestions as JSON (no auth needed)
```

**NLP Processing**:
- Unigram frequency analysis (title keywords weighted 3x)
- N-grams: bigrams, trigrams, 4-grams
- Co-occurrence pairs
- Filter stopwords + generic e-commerce terms
- Classify: primary (high-frequency bigrams) → secondary (trigrams) → long-tail (4-grams) → trending (autocomplete)

---

### Phase 2: AI Content Generation (Priority B)
**Goal**: Generate marketplace-compliant listings with one click

**Changes**:
- `modules/content_generator.py` — Remove mock fallback, add variation-aware generation, better prompts, retry logic, validation
- `routers/content.py` — Add generate-with-variations endpoint, validation endpoint
- `models.py` — VariationContent, ContentValidationResult models
- `database.py` — variation_content table, listing_status tracking

**Content Generation Flow**:
```
1. Read product details + selected keywords from DB
2. Build marketplace-specific prompt with:
   - Product specs (name, brand, category, material, dimensions)
   - Top 15 keywords from research (injected naturally)
   - Character limits per field
   - Marketplace-specific formatting rules
3. Call Gemini 2.5 Flash with response_mime_type="application/json"
4. Validate output against character limits
5. For variations: generate base content once, then adapt per variation
   - "BRAND Black Baseball Cap - Premium Cotton..." 
   - "BRAND Red Baseball Cap - Premium Cotton..."
6. Save all content back to DB
```

**Variation Content Strategy**:
- Base product content generated once
- Per-variation: title modified with color/size, description adapted
- Each variation is a separate row in Excel export

---

### Phase 3: Image-Based Product Detection (Priority C)
**Goal**: Upload a photo → auto-fill product form

**Changes**:
- `modules/vision_detector.py` — **NEW** — Gemini Vision API
- `routers/vision.py` — **NEW** — Image upload endpoint
- `index.html` — Drag-and-drop upload zone in wizard Step 1

**Vision Detection Prompt**:
```
Analyze this product image. Return JSON:
{
  "product_type": "baseball cap",
  "suggested_name": "Adjustable Cotton Baseball Cap",
  "category": "baseball_caps",
  "material": "cotton",
  "colors": ["black", "navy blue"],
  "key_features": ["adjustable strap", "breathable fabric", "embroidered logo"],
  "suggested_keywords": ["baseball cap", "cotton cap", "adjustable cap"],
  "confidence": 0.92
}
```

---

### Phase 4: Export & Preview (Priority A)
**Goal**: See formatted listing data in UI + download marketplace Excel

**Changes**:
- `modules/excel_exporter.py` — **NEW** — Real Excel generation with openpyxl
- `routers/templates.py` — Replace stubs with real preview + export
- `routers/pricing.py` — Auto-price products, save snapshots

**Excel Structure**:
- **Sheet "All Products"**: Every column, one row per variation
- **Sheet "Amazon"**: Only Amazon columns, matching Seller Central format
- **Sheet "Flipkart"**: Only Flipkart columns, matching Seller Hub format
- **Sheet "Meesho"**: Only Meesho columns, matching Supplier Hub format

**Columns per marketplace sheet**:
```
Amazon: SKU | Title | Brand | Bullet 1-5 | Description | Search Terms | Price | Category
Flipkart: SKU | Title | Brand | Key Feature 1-6 | Description | Keywords | Price | Category
Meesho: SKU | Title | Brand | Description | Price | Category
```

---

### Phase 5: Wizard UI Overhaul
**Goal**: Replace 7 disconnected pages with one guided wizard

**Changes**:
- `index.html` — Wizard modal, image upload, keyword selector, content preview, export table
- `app.js` — ProductWizard class, SSE listeners, bulk operations, Kanban board
- `styles.css` — Wizard steps, dropzone, keyword pills, side-by-side layout, Kanban

**Wizard Steps**:
```
Step 1: Product Info
├── Option A: Upload photo → auto-detect
├── Option B: Manual form entry
├── Add variations (color/size SKUs)
└── "Next" button

Step 2: Keyword Research
├── Auto-triggered on entering this step
├── SSE progress bar (real-time)
├── Results: frequency pills, n-grams table, co-occurrences
├── Checkboxes to select/deselect keywords
└── "Next" button

Step 3: Content Generation
├── Auto-triggered with selected keywords
├── Three-column preview: Amazon | Flipkart | Meesho
├── Click any field to edit inline
├── Character count indicators (green/red)
├── Per-variation tabs
└── "Next" button

Step 4: Pricing & Review
├── Auto-calculated from cost_price + target_margin
├── Fee breakdown per marketplace
├── Adjust margin slider → prices update live
├── Variation pricing table
└── "Next" button

Step 5: Export Preview
├── Full table preview in browser
├── Marketplace tabs (Amazon/Flipkart/Meesho/All)
├── "Download Excel" button
├── "Mark as Listed" checkbox per marketplace
└── "Done" button → back to dashboard
```

**Dashboard Kanban Board**:
```
| New (5) | Keywords Done (3) | Content Ready (7) | Priced (2) | Exported (12) | Listed (71) |
|---------|-------------------|-------------------|------------|---------------|-------------|
| Cap-001 | Cap-004           | Cap-007           | Cap-015    | Cap-020       | Cap-030     |
| ...     | ...               | ...               | ...        | ...           | ...         |
```

---

### Phase 6: Settings & Polish
**Changes**:
- `routers/settings.py` — **NEW** — API key management, default preferences
- `database.py` — app_settings table

---

## Database Schema (v2.0)

```sql
-- Existing tables (kept as-is)
products              -- Core product data + marketplace content
product_variations    -- Color/size variants
export_history        -- Export tracking
pricing_snapshots     -- Price calculation history
keyword_researches    -- Scraped keyword data (+ product_id link)

-- New tables
variation_content     -- Per-variation marketplace content
app_settings          -- Key-value app configuration

-- New columns
products.listing_status  -- Workflow state tracking
keyword_researches.product_id  -- Link research to product
```

---

## API Endpoints (v2.0)

| Method | Endpoint | Description | Phase |
|--------|----------|-------------|-------|
| POST | `/api/keywords/research` | Run keyword research | 1 |
| GET | `/api/keywords/research/stream` | SSE progress during research | 1 |
| GET | `/api/keywords/autocomplete` | Amazon autocomplete suggestions | 1 |
| GET | `/api/keywords/history` | Past research results | 1 |
| POST | `/api/content/generate` | Generate content for product | 2 |
| POST | `/api/content/generate-with-variations` | Generate for all variations | 2 |
| POST | `/api/content/validate` | Validate content limits | 2 |
| POST | `/api/vision/detect` | Detect product from image | 3 |
| POST | `/api/templates/preview` | JSON preview of export data | 4 |
| POST | `/api/templates/export` | Download Excel file | 4 |
| POST | `/api/pricing/calculate` | Calculate pricing | 4 |
| POST | `/api/pricing/auto-price/{product_id}` | Auto-price a product | 4 |
| GET/PUT | `/api/settings` | App configuration | 6 |
| POST | `/api/settings/test-gemini` | Validate API key | 6 |
| GET | `/api/products/` | List products (with listing_status) | 1 |
| POST | `/api/products/` | Create product | 1 |
| PUT | `/api/products/{id}` | Update product | 1 |
| DELETE | `/api/products/{id}` | Delete product | 1 |
| GET | `/api/products/stats/overview` | Dashboard stats + Kanban data | 5 |

---

## Environment Variables (.env)

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# App Settings
APP_HOST=127.0.0.1
APP_PORT=8000
DATABASE_PATH=data/listing_helper.db
EXPORT_PATH=data/exports
DEFAULT_TARGET_MARGIN=25

# Scraper Settings
HEADLESS_BROWSER=True
SCRAPER_MIN_DELAY=2
SCRAPER_MAX_DELAY=4
SCRAPER_MAX_RETRIES=2

# Optional (for future API integrations)
AMAZON_SP_API_REFRESH_TOKEN=
AMAZON_SP_API_CLIENT_ID=
AMAZON_SP_API_CLIENT_SECRET=
AMAZON_MARKETPLACE_ID=A21TJRUUN4KGV
FLIPKART_APP_ID=
FLIPKART_APP_SECRET=
```

---

## Running the Project

```bash
# Setup
cd c:\Automation\listing_helper
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure
# 1. Copy .env.example to .env
# 2. Add your Gemini API key

# Run
python main.py
# → Open http://localhost:8000

# Or with uvicorn directly
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

---

## Design Principles

1. **Wizard-first**: One guided flow beats 7 separate pages
2. **Preview-first**: Show data in UI before requiring downloads
3. **Variation-aware**: Every product can have color/size SKUs with tailored content
4. **Fail gracefully**: If scraping fails, show clear error (not fake mock data)
5. **Cache aggressively**: Never re-scrape the same URL
6. **Offline-capable**: Everything except AI generation works without internet
7. **Mobile-responsive**: Wizard works on tablet/phone for on-the-go listing

---

## Time Savings Projection

| Step | Manual | Automated | Saved |
|------|--------|-----------|-------|
| Product entry | 5 min | 1 min (15s with image scan) | ~4 min |
| Keyword research | 30-45 min | 3-5 min | ~35 min |
| Content writing (×3 MPs) | 45-60 min | 2 min | ~50 min |
| Pricing calculation | 10-15 min | Instant | ~12 min |
| Excel template filling | 15-20 min | 1-click | ~18 min |
| **Total per product** | **~2 hours** | **~10 minutes** | **~1h 50m** |
| **Monthly (100 products)** | **~200 hours** | **~17 hours** | **~183 hours** |
