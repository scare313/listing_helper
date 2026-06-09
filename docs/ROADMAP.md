# Roadmap

---

## Completed

| Feature | Phase | Notes |
|---|---|---|
| Product CRUD with variations | 1 | Full create/read/update/delete |
| Amazon keyword research (dual-strategy scraper) | 1 | requests+BS4 → Selenium fallback |
| SSE progress streaming | 1 | Real-time progress during scraping |
| NLP keyword analysis | 1 | n-grams, frequency, co-occurrence |
| Amazon autocomplete integration | 1 | Parallel to scraping |
| AI content generation (Gemini 2.5 Flash) | 2 | Amazon + Flipkart + Meesho |
| Variation-aware content generation | 2 | Per-variant adapted content |
| Content validation against marketplace limits | 2 | Character count checks |
| Image-based product detection (Gemini Vision) | 3 | Auto-fill product form |
| 4-sheet Excel export (openpyxl) | 4 | All Products + 3 marketplace sheets |
| Variation rows in Excel export | 4 | Sub-rows under parent product |
| Iterative pricing calculation | 4 | Converges to target margin ±0.1% |
| Batch pricing endpoint | 4 | Multiple products in one call |
| Export history tracking | 4 | `export_history` table |
| Settings management (Gemini key, scraper config) | 6 | DB-backed runtime overrides |
| 5-step wizard UI | 5 | Replaces 7 disconnected pages |
| Kanban dashboard | 5 | 6-column workflow board |
| `listing_status` workflow tracking | 5 | Products advance through stages |

---

## In Progress / Next Sprint

Items sourced from `NEXT_SPRINT.md`. Estimated effort in parentheses.

| Task | Priority | Effort | Description |
|---|---|---|---|
| TASK-02: Category-specific fee handling | High | 2–3h | Separate fee slabs for sports vs. home_kitchen categories |
| TASK-03: Variation pricing | High | 3–4h | `additional_cost` included in variation price calculations |
| TASK-05: Flipkart keyword format validation | Medium | 1–2h | Validate `::` delimiter format for Flipkart keywords field |
| TASK-06: Product form validation | Medium | 2–3h | Frontend required-field checks before Step 1 "Next" |
| TASK-07: Keyword selection persistence | Medium | 2–3h | Save selected keywords to DB, restore on wizard re-open |
| TASK-08: Content save on tab switch | Medium | 1–2h | Auto-save when switching variation tabs in Step 3 |
| TASK-09: Pricing snapshot history | Low | 2–3h | Show previous pricing snapshots in Step 4 |
| TASK-10: Export filename includes product SKU | Low | 1h | `CAP-BLK-001_listings_20260609.xlsx` format |
| TASK-11: Bulk product creation (CSV import) | Medium | 4–6h | Import products from spreadsheet |
| TASK-12: Dashboard search and filter | Medium | 2–3h | Filter Kanban by category or status |
| TASK-13: Content comparison view | Low | 3–4h | Side-by-side diff of AI-generated vs. edited content |
| TASK-14: Scraper status indicator | Low | 1–2h | Show Selenium/BS4/fallback status in UI |
| TASK-15: Error recovery UI | High | 3–4h | Clear error messages when Gemini or scraper fails |

---

## Planned (Future Phases)

### Marketplace API Integrations
Direct submission to marketplace portals without manual Excel upload.

- **Amazon SP-API**: Submit listings, update inventory, fetch order data.
  Credentials stub exists in `.env.example`. Requires SP-API developer account.
- **Flipkart Seller API**: Product listing submission.
- **Meesho Supplier API**: Product listing submission.

Estimated effort: 15–25 hours per marketplace.

### Competitor Analysis
- Scrape competitor product pricing and keyword usage
- Display price gap analysis in the pricing step
- Suggest keywords used by top-ranked competitors but missing from current listing
- Uses the reserved `competitor_data` column in the `products` table

### Listing Performance Tracking
- Enter marketplace order counts manually or via API
- Track which keyword strategies correlate with sales
- Alert when listing_status = 'listed' for 30+ days without orders

### Batch Wizard
- Select multiple products from the product list
- Run keyword research, content generation, and pricing for all selected products
  in sequence with a single click

### Real-Time Inventory Sync
- Connect to inventory management system (Tally, Zoho, or custom)
- Auto-update `stock_quantity` on variations
- Block export if stock is zero

### Image Management
- Store multiple images per product (main + lifestyle shots)
- Display images in the wizard and export preview
- Include image filenames in the Excel export

### Pricing Alerts
- Notify when marketplace fee structures change (requires periodic API or web check)
- Alert if calculated margin drops below threshold due to cost price or fee changes

---

## Deferred / Parking Lot

| Feature | Reason Deferred |
|---|---|
| Local LLM for content generation | User's PC not powerful enough for quality output |
| Real-time sales dashboard (marketplace APIs) | Requires SP-API approval process |
| Mobile app | Out of scope for local tool; web is mobile-responsive |
| Multi-user support with authentication | Single-user use case; complexity not justified |
| Flipkart/Meesho keyword scraping | No good public scraping target; low ROI |

---

## Technical Debt Roadmap

| Item | When to Address |
|---|---|
| Extract pricing logic to `modules/pricing_engine.py` (R-16) | Before adding any more pricing features |
| Split `app.js` into modules | When file exceeds 3000 lines or second developer joins |
| Add request logging middleware | Before any production deployment |
| Add explicit timeout to fast-path scraper requests | Next sprint |
| Fix version string `"1.0.0"` → `"2.0.0"` in `main.py` | Trivial — do it now |
