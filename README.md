# Listing Helper

> AI-powered product listing automation for Amazon India, Flipkart, and Meesho.

Listing Helper is a local web application that takes a seller from a blank product form to a
marketplace-ready Excel workbook in approximately 10 minutes — replacing a process that previously
took ~2 hours per product.

---

## Features

| Feature | Status |
|---|---|
| **5-step wizard workflow** — guided from product entry to export | ✅ Implemented |
| **AI content generation** — Gemini 2.5 Flash writes titles, bullets, descriptions per marketplace | ✅ Implemented |
| **Keyword research** — dual-strategy Amazon scraper (requests+BS4 → Selenium fallback) + NLP | ✅ Implemented |
| **Image-based product detection** — upload photo, auto-fill form | ✅ Implemented |
| **Pricing calculator** — reverse-calculates selling price to hit target margin, full fee breakdown | ✅ Implemented |
| **Excel export** — 4-sheet workbook (All Products + one sheet per marketplace) | ✅ Implemented |
| **Variation support** — per-variant content for color/size SKUs | ✅ Implemented |
| **Kanban dashboard** — 6-column workflow status board | ✅ Implemented |
| **Content validation** — checks every field against marketplace character limits | ✅ Implemented |
| **Settings management** — API key, scraper delays, default margin | ✅ Implemented |

---

## Screenshots

> _Screenshots pending — run the app and capture `http://localhost:8000`_

| Screen | Description |
|---|---|
| Dashboard | 6-column Kanban showing product workflow stages |
| Wizard Step 1 | Product form with drag-and-drop image detection |
| Wizard Step 2 | Keyword research with SSE progress stream |
| Wizard Step 3 | Three-column content editor (Amazon / Flipkart / Meesho) |
| Wizard Step 4 | Pricing calculator with fee breakdown |
| Wizard Step 5 | Export preview table + Excel download |
| Settings | Gemini API key, scraper config, default margin |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Google Gemini API key (free tier: 15 RPM) — obtain at https://aistudio.google.com/
- Google Chrome + ChromeDriver (only needed if Selenium fallback is used for scraping)

### Installation

```bash
# 1. Clone / download the repository
cd C:\Automation\listing_helper

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux

# 5. Edit .env — set at minimum:
#    GEMINI_API_KEY=your_key_here

# 6. Start the server
python main.py
```

Open **http://localhost:8000** in your browser.

---

## Architecture Summary

```
Browser (SPA)
    │  HTTP / SSE
    ▼
FastAPI (main.py)
    ├── /api/products     → products.py
    ├── /api/keywords     → keywords.py  ← streams SSE progress
    ├── /api/content      → content.py   ← calls Gemini API
    ├── /api/pricing      → pricing.py   ← pure calculation
    ├── /api/templates    → templates.py ← Excel export
    ├── /api/vision       → vision.py    ← Gemini Vision
    └── /api/settings     → settings.py
    
    Modules (business logic)
    ├── keyword_research.py   ← scraping + NLP
    ├── content_generator.py  ← Gemini prompts + retry
    ├── vision_detector.py    ← Gemini Vision
    └── excel_exporter.py     ← openpyxl workbook builder
    
    Data layer
    ├── database.py           ← aiosqlite async CRUD
    └── data/listing_helper.db
```

Full architecture diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Project Structure

```
listing_helper/
├── main.py                  # FastAPI app + router registration
├── config.py                # Settings, fee structures, category mappings
├── database.py              # SQLite schema + async CRUD
├── models.py                # Pydantic request/response models
├── requirements.txt
├── .env                     # Secrets (never commit)
├── .env.example             # Template
│
├── routers/
│   ├── products.py          # Product CRUD + variations
│   ├── keywords.py          # Keyword research + SSE stream
│   ├── content.py           # AI content generation
│   ├── pricing.py           # Fee calculation + auto-price
│   ├── templates.py         # Preview + Excel export
│   ├── vision.py            # Image product detection
│   └── settings.py          # App configuration
│
├── modules/
│   ├── keyword_research.py  # Scraper (BS4 + Selenium) + NLP
│   ├── content_generator.py # Gemini API prompts + retry
│   ├── vision_detector.py   # Gemini Vision API
│   └── excel_exporter.py    # openpyxl workbook generation
│
├── static/
│   ├── index.html           # Single-page application shell
│   ├── css/styles.css       # Glassmorphism dark theme
│   └── js/app.js            # SPA logic (~2500 lines)
│
├── data/
│   ├── listing_helper.db    # SQLite database (auto-created)
│   └── exports/             # Generated Excel files
│
└── docs/                    # This documentation
```

---

## Development Setup

```bash
# Run with hot-reload
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Interactive API docs (auto-generated by FastAPI)
open http://localhost:8000/docs

# Health check
curl http://localhost:8000/api/health
```

---

## Documentation

| Document | Contents |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, request flows, Mermaid diagrams |
| [DATABASE.md](docs/DATABASE.md) | Schema, relationships, workflow states |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | All endpoints, request/response examples |
| [WORKFLOWS.md](docs/WORKFLOWS.md) | Step-by-step workflow diagrams |
| [FRONTEND.md](docs/FRONTEND.md) | SPA structure, wizard architecture, state management |
| [BACKEND.md](docs/BACKEND.md) | Routers, modules, scraper, AI generation |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Local and production deployment |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | All settings, defaults, recommended values |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and diagnosis steps |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Coding standards, branching, PR guidelines |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | Non-technical step-by-step usage guide |
| [ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) | Operations: keys, backups, monitoring |
| [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | Technical and marketplace limitations |
| [CHANGELOG.md](docs/CHANGELOG.md) | Version history |
| [ROADMAP.md](docs/ROADMAP.md) | Completed, in-progress, and planned work |

---

## Time Savings

| Step | Manual | Automated | Saved |
|---|---|---|---|
| Product entry | 5 min | 1 min (15s with image scan) | ~4 min |
| Keyword research | 30–45 min | 3–5 min | ~35 min |
| Content writing (×3 marketplaces) | 45–60 min | 2 min | ~50 min |
| Pricing calculation | 10–15 min | Instant | ~12 min |
| Excel template filling | 15–20 min | 1-click | ~18 min |
| **Total per product** | **~2 hours** | **~10 minutes** | **~1h 50m** |
| **Monthly (100 products)** | **~200 hours** | **~17 hours** | **~183 hours** |

---

## License

Private / internal tool. Not licensed for public distribution.
