# Known Limitations

---

## Technical Limitations

### Single-Worker Only
The SSE keyword research stream uses an in-process `asyncio.Queue` to pass events from
the scraper task to the HTTP response generator. This design only works with a single
server process (`--workers 1`). Running multiple Uvicorn workers would route the SSE
response to a different process than the one running the scraper, causing the stream to
hang indefinitely. Tracked: replace queue with Redis pub/sub if multi-worker support
is ever needed.

### No Request Timeout in Fast-Path Scraper
`_scrape_fast_path_sync` does not set an explicit `timeout=` on `requests.get()` calls.
If Amazon serves an extremely slow response, the thread pool worker can hang indefinitely.
Mitigated in practice by the SSE stream's client-side timeout, but not formally bounded.

### Scraper Reliability
The fast-path scraper parses Amazon HTML by CSS selector IDs (`#productTitle`,
`#feature-bullets`, etc.). Amazon changes its HTML structure periodically. When selectors
break, the scraper returns empty results and falls through to the local fallback.
Symptoms: all keyword research returns template keywords rather than real data.
Fix: update CSS selectors in `_scrape_fast_path_sync`.

### Selenium ChromeDriver Version Drift
The Selenium fallback requires a ChromeDriver version that exactly matches the installed
Chrome browser. Chrome auto-updates; ChromeDriver does not. After a Chrome update, the
fallback will fail with a version mismatch error until ChromeDriver is manually updated.
Mitigation: pin Chrome version, or switch to `webdriver-manager` for automatic version
matching.

### No Request Logging
The application has no HTTP access log middleware. There is no audit trail of which
endpoints were called, when, or with what parameters. FastAPI's built-in `uvicorn` access
log covers only raw HTTP, not structured request data.

### CORS Wildcard
`CORSMiddleware` is configured with `allow_origins=["*"]`. Acceptable for a localhost-only
tool, but dangerous if the app is exposed on a network. Should be locked to specific
origins for any non-local deployment.

### Frontend — No Error Boundary
Unhandled JavaScript exceptions in render functions propagate up and can leave the UI in
a broken state (e.g., Kanban board not rendering, wizard step blank). There is no global
error handler that shows a fallback UI. The user must refresh the page to recover.

### Frontend — Global Mutable State
All wizard state is stored in module-level `let` variables in `app.js`. There is no state
management system. Bugs where state from a previous wizard session "leaks" into a new
session are possible if `closeWizard()` doesn't clear all variables.

### Frontend — Large Product Catalog Performance
`renderDashboard()` fetches up to 200 products on every page visit and builds the DOM
synchronously. With 200+ products the dashboard will noticeably lag. The Kanban board
should be paginated or virtualised at scale.

### Version String Mismatch
`main.py` declares `version="1.0.0"` in the FastAPI constructor but the documentation
and `CLAUDE.md` refer to `v2.0`. The `/api/health` endpoint returns `"version": "1.0.0"`.

### Pricing Logic Not Modularised
The pricing calculation functions (`_calculate_marketplace_pricing`,
`_calculate_target_price`) live in `routers/pricing.py` rather than
`modules/pricing_engine.py`. This violates the thin-router principle and makes it
harder to unit-test pricing logic independently. Tracked as R-16.

---

## Marketplace Limitations

### Amazon — Scraping Risk
The scraper reads public Amazon.in pages without authentication. Amazon actively
detects and blocks scrapers. While the app uses randomised User-Agent rotation and
human-like delays, Amazon may still block requests, especially:
- After many research runs in a short period
- From cloud/VPS IP addresses (use on a home/office connection)
- If Amazon updates anti-bot measures

When blocked, keyword research degrades to local template keywords. No account or legal
risk to the seller — only public pages are read.

### Amazon — No Seller Central API Integration
The app cannot programmatically submit listings to Amazon Seller Central. The SP-API
credentials in `.env.example` are reserved for a future integration that is not yet
implemented. Listings must be uploaded manually via the Amazon Seller Central bulk
upload tool.

### Flipkart and Meesho — No Scraping
Keyword research only scrapes Amazon. There is no equivalent keyword research for
Flipkart or Meesho. The same Amazon-derived keywords are used for all three marketplaces,
which is a reasonable approximation but not optimal for Flipkart/Meesho-specific search
behaviour.

### Flipkart and Meesho — No API Integration
Like Amazon, there is no API integration for submitting listings to Flipkart Seller Hub
or Meesho Supplier Hub. Excel export + manual upload is the current workflow.

### Fee Structure Accuracy
Marketplace fee structures are hardcoded in `config.py`. Marketplaces change their fee
slabs periodically (typically quarterly). If fees change, `config.py` must be manually
updated. Stale fees will produce incorrect pricing calculations.

The current fee structures were correct as of the initial implementation date. Verify
against the official fee pages before making large pricing decisions:
- Amazon: https://sell.amazon.in/fees-and-pricing
- Flipkart: https://seller.flipkart.com/fees
- Meesho: https://supplier.meesho.com/

---

## AI Limitations

### Hallucination Risk
Gemini may generate factually incorrect product claims (e.g., claiming a cap is
waterproof when it is not). All AI-generated content must be reviewed before publishing.
The more specific your product details and notes, the more accurate the output.

### Character Limit Compliance
Content generation includes character limits in the prompt and the app validates output
post-generation. However, Gemini occasionally generates content that marginally exceeds
limits (especially for Flipkart's 10 features at 200 chars each). The validation step
shows a warning but does not block the export. Fields over the limit will be rejected
by the marketplace's import tool and must be shortened manually.

### Variation Content Drift
Variation content is generated by asking Gemini to adapt a base product's content for
each variant. For products with many variations, early and late variations may have
inconsistent tone or emphasis. Review all variation tabs before exporting.

### Gemini Model Hardcoded
The model is hardcoded as `gemini-2.5-flash` in `content_generator.py` and
`vision_detector.py`. The `gemini_model` setting in the Settings UI is stored in the
database but not actually read by any code — it is informational only. To change the
model, edit the source files directly.

---

## Operational Limitations

### No Multi-User Support
The application has no user authentication. It is designed for a single user on a local
machine. If multiple users access the same instance simultaneously, Kanban drag-and-drop
and wizard state will not be isolated between sessions.

### No Undo / History
There is no undo for content edits or product deletions. The `products.updated_at`
timestamp shows when a product was last changed, but there is no content version history.
Before deleting a product, export it first.

### `competitor_data` Column Unused
The `competitor_data` TEXT column exists in the `products` table and Pydantic models but
no code reads from or writes to it. It was reserved for a competitor analysis feature
that has not been implemented.
