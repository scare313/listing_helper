# Workflows

## Overview

Every product follows a linear 5-step wizard workflow. Each step has a defined entry
state, an action, and an exit state that advances the product on the Kanban board.

```
┌──────────┐    ┌─────────────────┐    ┌───────────────┐    ┌────────┐    ┌──────────┐    ┌────────┐
│   new    │───►│  keywords_done  │───►│ content_ready │───►│ priced │───►│ exported │───►│ listed │
└──────────┘    └─────────────────┘    └───────────────┘    └────────┘    └──────────┘    └────────┘
  Step 1            Step 2               Step 3              Step 4          Step 5        Manual
  Product           Keyword              AI Content          Pricing         Excel         checkbox
  Form              Research             Generation          Calc            Download
```

---

## Product Creation Workflow (Step 1)

```
User opens wizard
    │
    ├── Option A: Drag-and-drop image
    │     │  POST /api/vision/detect
    │     ▼
    │   Gemini Vision returns:
    │     product_type, suggested_name, category,
    │     material, colors, key_features, keywords,
    │     suggested_weight_grams, suggested_hsn_code
    │     │
    │     └── Auto-fill wizard form fields
    │
    └── Option B: Manual entry
          Fill: name, sku, brand, category, cost_price,
                weight_grams, dimensions, hsn_code, notes

User adds variations (optional)
    │  Each row: variation_type, variation_value, variation_sku
    │
    ▼
Click "Next"
    │  POST /api/products/  (create) or PUT /api/products/{id}  (update)
    │  For each new variation: POST /api/products/{id}/variations
    ▼
listing_status = 'new' (or updated)
wizardProduct set in memory
wizardVariations populated
```

---

## Keyword Research Workflow (Step 2)

```
User enters seed keyword (or URL from Amazon bestseller page)
    │
    ▼
Click "Start Research"
    │  GET /api/keywords/research/stream?seed=...&limit=25&product_id=...
    │
    ▼  SSE stream begins
    │
    ├── Strategy 1: requests + BeautifulSoup
    │     ├── Fetch search/bestseller page
    │     ├── Extract up to limit product /dp/ links
    │     └── Fetch each product page (2–4s delay between requests)
    │           Parse: title, bullet points, description
    │
    ├── [If blocked by 503/429/CAPTCHA]
    │     └── Strategy 2: Selenium headless Chrome
    │           Same scraping flow, real browser rendering
    │
    ├── [If both strategies fail]
    │     └── Local fallback: template keywords from seed word
    │
    ├── NLP Analysis
    │     ├── Weighted unigram frequency (titles 3×, bullets+desc 1×)
    │     ├── Bigrams, trigrams, 4-grams with stopword filtering
    │     └── Co-occurrence pairs
    │
    └── Amazon Autocomplete API (parallel)
          GET completion.amazon.in/api/2017/suggestions?prefix=...

SSE "complete" event fires → renderWizardKeywordResults(results)
    │
    ▼
Display keyword pills (primary) and secondary keywords
User checks/unchecks pills to select keywords

Click "Next"
    │  POST /api/keywords/apply-to-product?product_id=...&keywords=...
    │  Saves to products.keywords_data.applied_keywords
    ▼
listing_status updated to 'keywords_done' (implicit via product update)
```

---

## AI Content Generation Workflow (Step 3)

```
Step 3 loads
    │  loadWizardStep3Content()
    │  GET /api/products/{id}/variation-content
    ▼
Editor pre-filled with any existing content

User clicks "Generate AI Copies"
    │
    ├── [No variations] POST /api/content/generate
    │     {product_id, marketplace: 'all', keywords: selectedKeywords}
    │
    └── [Has variations] POST /api/content/generate-with-variations
          {product_id, keywords: selectedKeywords}

AI generation flow (per marketplace):
    │
    ├── Build prompt: product specs + top 15 keywords + marketplace rules
    ├── Call Gemini API (response_mime_type=application/json)
    │     Retry on 429/503 with exponential backoff: 1s, 2s, 4s, 8s, 16s
    ├── Parse JSON response
    ├── Validate against MARKETPLACE_LIMITS (log warnings)
    └── Save to products table (amazon_status/flipkart_status/meesho_status = 'ready')

[For variations]
    ├── Generate base content (all 3 marketplaces)
    └── For each variation:
          Generate adapted content with variation_info injected into prompt
          Save to variation_content table

Content appears in 3-column editor (Amazon | Flipkart | Meesho)
User can edit any field inline
Character counters update in real time

Variation tabs shown if product has variations
    Click tab → load that variation's content
    "Base Product" tab shows the master copy

Click "Next"
    │  Content validation (POST /api/content/validate × 3 marketplaces)
    │  Warning toast if any field exceeds limits (non-blocking)
    │  PUT /api/products/{id}  (save edited content)
    ▼
listing_status = 'content_ready' (set by content generation endpoint)
```

---

## Pricing Workflow (Step 4)

```
Step 4 loads
    │  calculateWizardPricing() fires automatically
    │
    ▼
POST /api/pricing/calculate
    {
      product_id: wizardProduct.id,
      cost_price, weight_grams, category,
      target_margin: 25.0,
      shipping_zone: 'national'
    }

Backend calculation:
    │
    ├── Amazon
    │     referral_fee = selling_price × 10%  (sports_and_fitness)
    │     closing_fee  = ₹9  (₹251–500 slab)
    │     shipping_fee = ₹57 (0–500g, national)
    │     gst_on_fees  = 18% of above
    │     profit       = selling_price - cost - total_fees
    │
    ├── Flipkart
    │     commission   = selling_price × 8%
    │     fixed_fee    = ₹11 (₹251–500 slab)
    │     shipping     = ₹57 (0–500g, national)
    │     collection   = max(₹5, min(price × 2%, ₹25))
    │     gst_on_fees  = 18%
    │
    └── Meesho
          commission   = 0%  (Meesho USP)
          shipping     = ₹65 (0–500g, national)
          gst_on_ship  = 18%

Saves: 3 pricing_snapshots rows + updates amazon_price, flipkart_price, meesho_price

User sees fee breakdown cards per marketplace
User can adjust margin slider (recalculates in real time)

Click "Next"
    ▼
listing_status = 'priced'
```

---

## Export Workflow (Step 5)

```
Step 5 loads
    │  loadWizardStep5Preview()
    │  POST /api/templates/preview {product_ids: [id], marketplace: 'all'}
    ▼
Preview table rendered in browser
Marketplace filter tabs: All / Amazon / Flipkart / Meesho

User selects marketplace tab → table re-fetches with that filter
    │  Requests /templates/preview with marketplace='amazon' etc.
    ▼
Filtered columns displayed

User checks "Mark as Listed" checkboxes for each published marketplace

User clicks "Download & Finish"
    │  POST /api/templates/export {product_ids: [id], marketplace: 'all'}
    │
    ▼
Excel file generated (data/exports/all_listing_export_{timestamp}.xlsx):
    Sheet 1: "All Products" — all columns, all marketplaces
    Sheet 2: "Amazon"       — Amazon-only columns
    Sheet 3: "Flipkart"     — Flipkart-only columns
    Sheet 4: "Meesho"       — Meesho-only columns
    
Variation rows appear beneath each product row.
Header colours: navy (All), orange (Amazon), blue (Flipkart), purple (Meesho).

Browser downloads file automatically
Export record written to export_history table

[If "Mark as Listed" checked]
    PUT /api/products/{id}
    {amazon_status: 'listed', listing_status: 'listed'}

Wizard closes
listing_status = 'exported' or 'listed'
```

---

## Listing Publication Workflow

After the Excel export, the seller publishes listings manually on each marketplace portal.
The application tracks publication status via per-marketplace status fields.

```
Marketplace Statuses
    ├── draft    — content not yet generated
    ├── ready    — content generated, not yet published
    └── listed   — manually confirmed as published

Workflow Kanban Status
    ├── new             — product created
    ├── keywords_done   — keywords researched and applied
    ├── content_ready   — AI content generated
    ├── priced          — pricing calculated
    ├── exported        — Excel downloaded
    └── listed          — confirmed as live on at least one marketplace
```

Products move between Kanban columns via:
1. Wizard step completion (automatic)
2. Drag-and-drop on the dashboard Kanban board (PUT /api/products/{id} with listing_status)
3. "Mark as Listed" checkboxes in wizard Step 5
