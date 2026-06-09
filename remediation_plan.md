# Remediation Plan — Listing Helper v2.0

> **Based on**: `implementation_audit.md` (2026-06-09)  
> **Target completion**: 95% (from current 72%)  
> **Sprint vehicle**: `NEXT_SPRINT.md`

---

## Summary Table

| ID | Title | Severity | Effort |
|---|---|---|---|
| R-01 | Settings UI reads/writes localStorage only | Critical | M |
| R-02 | Wizard Step 1 — no variation management UI | Critical | L |
| R-03 | Wizard content generation ignores variations | Critical | S |
| R-04 | Missing `/api/pricing/auto-price/{product_id}` | Critical | S |
| R-05 | Wizard Step 3 — no character count indicators | High | S |
| R-06 | Wizard Step 3 — no per-variation content tabs | High | L |
| R-07 | Wizard Step 5 — no "Mark as Listed" per marketplace | High | S |
| R-08 | Wizard Step 5 — no marketplace filter tabs | High | M |
| R-09 | Content validation not called from wizard flow | High | S |
| R-10 | Flipkart title limit display: 100 vs 500 chars | Medium | XS |
| R-11 | `saveWizardStep4()` is a no-op (prices not saved mid-wizard) | Medium | S |
| R-12 | Step 5 export preview response parsing fragile | Medium | XS |
| R-13 | Vision auto-fill missing weight and HSN fields | Medium | XS |
| R-14 | Blanket `except Exception` in keyword_research.py | Low | S |
| R-15 | `ContentValidationResult` model name mismatch in docs | Low | XS |
| R-16 | Pricing engine inline in router (architecture violation) | Low | M |
| R-17 | No automated test suite | Low | XL |

> **Effort key**: XS = <30min, S = 30-90min, M = 2-4hr, L = 4-8hr, XL = 1-2 days

---

## R-01 — Settings UI reads/writes localStorage only

**Severity: Critical**

### Why It Matters
The Settings page is the gateway to all runtime configuration: the Gemini API key (required for AI content generation and vision detection), the headless browser toggle (required for visible Selenium scraping), and default margin. Currently the UI saves to browser `localStorage` exclusively — meaning the DB-backed `app_settings` table, the entire `routers/settings.py`, and the `GET/PUT /api/settings` endpoints are functionally bypassed. If the user opens in a different browser or clears storage, all configuration is lost. More critically, the server never reads the key from DB into `settings.GEMINI_API_KEY` at runtime, so the DB-saved key has zero effect on AI generation.

**Audit finding**: `saveSettings()` (line 1566) and `loadSettings()` (line 1579) use `localStorage`. Separately, `renderSettings()` (line 1460) already calls `GET /api/settings` and pre-fills form fields from `dbSettings` — and `saveDbSettings()` (line 1533) already calls individual `PUT /api/settings/{key}` endpoints. These two correct functions exist but are never called from the Settings page.

### Files Involved
- `static/js/app.js` — lines 1460–1587
  - `renderSettings()` already correctly loads from API
  - `saveDbSettings()` already correctly saves to API  
  - `saveSettings()` (localStorage, dead code)
  - `loadSettings()` (localStorage, dead code)
  - The Settings page HTML rendered inside `renderSettings()` buttons call `saveSettings()` — should call `saveDbSettings()`
- `routers/settings.py` — Already correct, no changes needed
- `config.py` — `settings.GEMINI_API_KEY` — consider whether the server should hot-reload from DB on each request

### Recommended Fix
1. In `renderSettings()` (line 1528), change the "Save Configurations" button's `onclick` from `saveSettings()` to `saveDbSettings()`. The function already exists and is correct.
2. Remove or comment out the dead `saveSettings()` (line 1566–1576) and `loadSettings()` (line 1579–1587) functions.
3. Verify that `renderSettings()` correctly maps `dbSettings` fields to the form inputs — specifically `gemini_api_key` field: the input `s-gemini-key` should show `dbSettings.gemini_api_key || ''` (already done at line 1482).
4. For the server to pick up a DB-stored Gemini key at runtime: in `modules/content_generator.py`'s `_call_gemini()`, after the key-not-configured check, add a fallback that calls `asyncio.run(get_setting('gemini_api_key'))` if `settings.GEMINI_API_KEY` is empty. This ensures a DB-saved key is honoured without requiring a server restart.

**Estimated effort: M (2–3 hours)** — The button onclick fix is trivial (XS). The server-side hot-reload of the API key from DB is the substantive work.

---

## R-02 — Wizard Step 1 — no variation management UI

**Severity: Critical**

### Why It Matters
CLAUDE.md Phase 5 explicitly requires "Add variations (color/size SKUs)" in Wizard Step 1. Without this, the entire variation-aware backend pipeline (R-03) cannot be triggered from the wizard. A seller listing a baseball cap in 5 colors must exit the wizard and use the standalone product modal to add variations — breaking the guided workflow.

The variation management UI exists in the standalone `product-modal` (index.html, line 103–200), but that modal has no variations section either — it only has basic product info. The `add_variation` API endpoint and `create_variation` database function are fully implemented.

### Files Involved
- `static/index.html` — `#wcontent-1` (line 238–303) — needs variation rows appended below the manual details form
- `static/js/app.js` — `openProductWizard()` (line 1883) — needs to load existing variations; `saveWizardStep1()` (line 2209) — needs to also save/sync variations
- `static/css/styles.css` — add variation row grid style (minimal, reuse existing `.form-grid`)

### Recommended Fix
1. **HTML** (`index.html`, `#wcontent-1`): After the "Manual Details" form grid (after line 302, before `</div>`), add a "Product Variations" section. It should contain:
   - A heading "Variations (Optional)"
   - A dynamic container `id="w-variations-container"` that holds one row per variation
   - Each row: `variation_type` dropdown (Color / Size / Material / Other), `variation_value` input, `sku` input, and a "Remove" button
   - An "Add Variation" button that calls `addWizardVariation()`
2. **JS** (`app.js`): Add the following functions:
   - `addWizardVariation()` — appends a new row to `#w-variations-container`
   - `removeWizardVariation(rowEl)` — removes the row
   - `getWizardVariations()` — reads all variation rows and returns array of `{variation_type, variation_value, sku}`
3. **JS** (`openProductWizard()`): After loading product fields (line 1911–1919), also call `GET /api/products/{id}/variations` and render existing variations into `#w-variations-container`.
4. **JS** (`saveWizardStep1()`): After saving the product, iterate `getWizardVariations()`. For each:
   - If it has a DB id (editing), skip (variations are add-only for now)
   - If new, call `POST /api/products/{id}/variations` for each variation
   - Store the resulting variation IDs in a `wizardVariations = []` module-level state variable

**Estimated effort: L (5–6 hours)** — Involves HTML, CSS, and JS coordination.

---

## R-03 — Wizard content generation ignores variations

**Severity: Critical**

### Why It Matters
`startWizardContentGeneration()` (line 2411) calls `POST /api/content/generate` which generates content for the base product only. The fully implemented `POST /api/content/generate-with-variations` endpoint — which generates tailored titles and bullets per color/size variant — is never invoked from the wizard. This means all variation content in the `variation_content` table remains empty in the wizard flow, and the per-variation rows in the Excel export will fall back to parent content.

### Files Involved
- `static/js/app.js` — `startWizardContentGeneration()` lines 2411–2442
  - Line 2430: `await api('/content/generate', 'POST', {product_id: wizardProduct.id, marketplace: 'all'})`
  - Should become: check if `wizardVariations.length > 0`, if so call `/content/generate-with-variations`, else call `/content/generate`

### Recommended Fix
1. At line 2430, replace the single `/content/generate` call with a conditional:
   - If `wizardVariations` state array (introduced in R-02) has length > 0, call `POST /api/content/generate-with-variations` with `{product_id: wizardProduct.id, keywords: selectedWizardKeywords}`
   - If no variations exist, fall back to `POST /api/content/generate` (existing behaviour)
2. After the API call succeeds, call `loadWizardStep3Content()` as it already does to populate the editor fields from the DB response.
3. Add an overlay message distinguishing the two cases: "Generating for base product + N variations" vs "Generating for base product".

**Note**: This task depends on R-02 completing first (to have `wizardVariations` state variable).

**Estimated effort: S (45 minutes)** — Single conditional branch change.

---

## R-04 — Missing `/api/pricing/auto-price/{product_id}` endpoint

**Severity: Critical**

### Why It Matters
CLAUDE.md's API endpoints table explicitly lists `POST /api/pricing/auto-price/{product_id}` as a required endpoint. While the existing `/api/pricing/calculate` already saves snapshots and prices to DB when `product_id` is supplied, the CLAUDE.md-specified endpoint does not exist. Any future integrations or direct API consumers expecting this endpoint will get a 404. More practically, the wizard's pricing step (`calculateWizardPricing()`) calls `/pricing/calculate` but could be made simpler and more intention-revealing by using a dedicated auto-price endpoint.

### Files Involved
- `routers/pricing.py` — needs a new route after line 213
- `models.py` — `PricingRequest` already has all needed fields; may need a simpler `AutoPriceRequest` (just `target_margin`, `shipping_zone`)

### Recommended Fix
Add `POST /api/pricing/auto-price/{product_id}` to `routers/pricing.py`. This endpoint should:
1. Accept `product_id` as a path parameter
2. Accept optional `target_margin` and `shipping_zone` as query params (defaulting to app settings values)
3. Read the product from DB (`get_product(product_id)`) to get `cost_price`, `weight_grams`, `category`
4. Call the existing `_calculate_target_price()` and `_calculate_marketplace_pricing()` private functions for all 3 marketplaces
5. Save snapshots and update product prices (same as the existing `/calculate` flow)
6. Return the same `PricingResponse` structure
7. This is essentially a thin wrapper that reads product data from DB rather than requiring the caller to supply it

**Estimated effort: S (45 minutes)** — Pure backend, reusing existing private functions.

---

## R-05 — Wizard Step 3 — no character count indicators

**Severity: High**

### Why It Matters
CLAUDE.md Phase 5 Step 3 explicitly requires "Character count indicators (green/red)". The standalone Content editor page already has `char-counter` CSS class, `#cnt-title`, `#cnt-desc`, `#cnt-kw` counter divs, and `runLiveKeywordChecker()` that updates them with colour-coded warnings. Wizard Step 3 (`#wcontent-3`) has plain `<input>` and `<textarea>` elements with no counters. Sellers editing AI-generated content in the wizard have no real-time feedback on whether they've exceeded Amazon's 200-char title limit, Flipkart's 5000-char description limit, etc.

### Files Involved
- `static/index.html` — `#wcontent-3` (lines 339–391) — inputs `#w-amazon-title`, `#w-amazon-bullets`, `#w-amazon-desc`, `#w-flipkart-title`, `#w-flipkart-features`, `#w-flipkart-desc`, `#w-meesho-title`, `#w-meesho-desc`
- `static/js/app.js` — needs a `setupWizardStep3Counters()` function, called from `goToWizardStep(3)` or `loadWizardStep3Content()`
- `static/css/styles.css` — `.char-counter` class already exists; `.char-counter.warning` and `.char-counter.danger` already exist

### Recommended Fix
1. **HTML** (`index.html`, `#wcontent-3`): After each input/textarea in each marketplace column, add a `<div class="char-counter" id="w-cnt-{field}">0 / {limit} chars</div>`. Limits from CLAUDE.md: Amazon title 200, Amazon description 2000, Flipkart title 500, Flipkart description 5000, Meesho title 200, Meesho description 2000.
2. **JS** (`app.js`): Add `attachWizardStep3Counters()` function that attaches `input` event listeners to each field in `#wcontent-3`. Each listener calls a helper `updateCounter(inputEl, counterEl, limit, isBytes)` — mirroring the logic in `runLiveKeywordChecker()` (line 1053).
3. **JS**: Call `attachWizardStep3Counters()` once when `loadWizardStep3Content()` resolves, and also after `startWizardContentGeneration()` populates the fields.

**Estimated effort: S (60 minutes)** — Mechanical reuse of existing counter pattern.

---

## R-06 — Wizard Step 3 — no per-variation content tabs

**Severity: High**

### Why It Matters
CLAUDE.md Phase 5 Step 3 requires "Per-variation tabs". When a product has variations (Black Cap, Red Cap, Blue Cap), the wizard should show tabs so the seller can review each variant's tailored title and description — not just the base product. Without tabs, the seller sees only the base content and has no way to verify that "BRAND Red Baseball Cap..." was correctly generated for the Red variant.

**Note**: This task depends on R-02 and R-03 being complete, since variations must first exist and variation-aware generation must be triggered.

### Files Involved
- `static/index.html` — `#wcontent-3` header area (line 340–345) — tab strip to be injected
- `static/js/app.js` — `loadWizardStep3Content()` (line 2386) — populates `#wcontent-3` editor fields
- `static/css/styles.css` — add `.wizard-variation-tabs` and `.wizard-variation-tab` styles (small addition)

### Recommended Fix
1. **JS** (`loadWizardStep3Content()`): After generating/loading content, also call `GET /api/products/{id}/variations` to fetch the list of variations.
2. **JS**: Render a tab strip above the marketplace columns in `#wcontent-3`. One tab labelled "Base Product" and one tab per variation (e.g., "Black", "Red"). The active tab's content is displayed in the three-column editor.
3. **JS**: When a variation tab is clicked, call `GET /api/products/{id}/variations` and then read from `variation_content` (via the preview endpoint or a new dedicated fetch) to populate the editor fields with that variation's content. Allow editing.
4. **JS** (`saveWizardStep3()`): When saving, detect which tab is active. If it's a variation tab, call `PUT /api/products/{variation_id}/variation-content` (if that endpoint exists) or `POST /api/content/generate-with-variations` to regenerate. For manual edits, call the product update endpoint appropriately.
5. **CSS**: A simple horizontal tab strip reusing existing `.tab` class pattern from the standalone Content editor page.

**Estimated effort: L (6–7 hours)** — Most complex UI task in this sprint.

---

## R-07 — Wizard Step 5 — no "Mark as Listed" per marketplace

**Severity: High**

### Why It Matters
CLAUDE.md Phase 5 Step 5 requires: "'Mark as Listed' checkbox per marketplace". This is the completion signal for the workflow — telling the system that a listing has been published on a given marketplace. Without it, products stay in "exported" status forever and the Kanban board never shows them as "Listed". The seller loses tracking of which marketplaces a product has actually gone live on.

### Files Involved
- `static/index.html` — `#wcontent-5` (lines 441–456) — needs checkboxes added
- `static/js/app.js` — `finishWizard()` (line 2612) — needs to read checkbox states and call `PUT /api/products/{id}` with `amazon_status`, `flipkart_status`, `meesho_status` set to "listed"

### Recommended Fix
1. **HTML** (`index.html`, `#wcontent-5`): After the preview table container (line 455), add a "Mark as Listed" row:
   - Three checkboxes with labels: `[☐] Listed on Amazon`, `[☐] Listed on Flipkart`, `[☐] Listed on Meesho`
   - IDs: `#w-listed-amazon`, `#w-listed-flipkart`, `#w-listed-meesho`
   - Small descriptive text: "Check each marketplace where you've published the listing"
2. **JS** (`finishWizard()`, line 2612): After downloading the Excel (line 2651), also read the three checkbox states. For each checked marketplace, include `{amazon_status: 'listed'}` (or flipkart/meesho equivalent) in the `PUT /api/products/{id}` call. The product update endpoint already accepts these fields via `ProductUpdate` model.

**Estimated effort: S (45 minutes)** — Small HTML + trivial JS addition.

---

## R-08 — Wizard Step 5 — no marketplace filter tabs

**Severity: High**

### Why It Matters
CLAUDE.md Phase 5 Step 5 requires "Marketplace tabs (Amazon/Flipkart/Meesho/All)". The current preview table shows all columns simultaneously, making it extremely wide and hard to review. Sellers need to verify that the Amazon-specific content (bullets, search terms) is correct before downloading — they shouldn't have to scroll past 30+ columns. The preview endpoint already accepts a `marketplace` parameter.

### Files Involved
- `static/index.html` — `#wcontent-5` (lines 441–456) — tab strip to add before the table
- `static/js/app.js` — `loadWizardStep5Preview()` (line 2557) — add `activePreviewMarketplace` state; re-call on tab switch

### Recommended Fix
1. **HTML** (`index.html`, `#wcontent-5`): Before the `.export-preview-table-container` (line 446), add a tab strip:
   - 4 tabs: "All", "Amazon", "Flipkart", "Meesho"
   - Each tab has `onclick="switchPreviewTab('all')"` (or amazon/flipkart/meesho)
   - Active tab gets `.active` class; style reuses existing `.tab` class
2. **JS** (`app.js`): Add module-level variable `let activePreviewMarketplace = 'all'`.
3. **JS**: Add `switchPreviewTab(mp)` function that sets `activePreviewMarketplace = mp`, updates active tab styling, and re-calls `loadWizardStep5Preview()`.
4. **JS** (`loadWizardStep5Preview()`): Change the `POST /templates/preview` body to use `marketplace: activePreviewMarketplace` instead of hardcoded `'all'`.
5. **JS**: When rendering the preview table, dynamically generate column headers based on the active marketplace (Amazon shows only Amazon columns, etc.) to avoid the 30-column sprawl.

**Estimated effort: M (2–3 hours)** — Tab logic + dynamic column header generation.

---

## R-09 — Content validation not called from wizard flow

**Severity: High**

### Why It Matters
The `POST /api/content/validate` endpoint exists and is fully implemented. The standalone Content editor has a "Validate" button. But the wizard never calls it — so a seller can proceed from Step 3 to Step 4 with an Amazon title that is 220 characters (20 over the limit) and never receive a warning. Validation failures only appear in server logs, not in the UI.

### Files Involved
- `static/js/app.js` — `saveWizardStep3()` (line 2447) — the gate between Step 3 and Step 4
- `static/css/styles.css` — `.validation-warning` and `.validation-error` already exist (reuse)

### Recommended Fix
1. **JS** (`saveWizardStep3()`, line 2447): Before returning `true` and advancing the step, construct validation payloads for each marketplace from the current field values.
2. For each marketplace call `POST /api/content/validate` with the title, bullets/features, description, and keywords. If any field returns `is_valid: false`, show a toast warning: "Amazon title is 215/200 chars — consider shortening before export".
3. The warning should be non-blocking (the seller can choose to proceed anyway), but the `Next` button's label should change to "Next (with warnings)" and display the issues in a collapsible list beneath the marketplace columns.
4. If all validations pass, show a green toast "All fields within marketplace limits" and advance normally.

**Estimated effort: S (60–75 minutes)** — API call + warning UI.

---

## R-10 — Flipkart title limit display: 100 vs 500 chars

**Severity: Medium**

### Why It Matters
The standalone Content editor shows "0 / 100 chars" for Flipkart title (line 1012 in app.js). CLAUDE.md, `config.py` (`MARKETPLACE_LIMITS`), and the content generator prompt all state 500 characters. This is a data inconsistency — the editor underreports the limit by 5×, causing sellers to unnecessarily truncate Flipkart titles.

### Files Involved
- `static/js/app.js` — line ~1012 where `0 / 100 chars` is hardcoded in the rendered HTML for the Flipkart title counter

### Recommended Fix
Locate the hardcoded `0 / 100 chars` string in `renderContent()` or `renderContentWorkspace()` (around line 830–1050) and change it to `0 / 500 chars`. Also update the corresponding `max` variable used in the counter update logic to `500`. Search for `100` near `flipkart` context to find all instances.

**Estimated effort: XS (<15 minutes)** — One-line fix, but verify all counter-related references.

---

## R-11 — `saveWizardStep4()` is a no-op (prices not saved mid-wizard)

**Severity: Medium**

### Why It Matters
`saveWizardStep4()` (line 2547) only calls `calculateWizardPricing()` and returns `true`. The calculated prices are stored only in `wizardPricingResult` (a JS variable). They are not saved to the database until `finishWizard()` is called — but `finishWizard()` only updates `listing_status` to `exported`, not the prices. If a user closes the wizard after Step 4 (before reaching Step 5 and finishing), all pricing work is lost. Also, the product's `amazon_price`, `flipkart_price`, `meesho_price` fields are only saved if `calculateWizardPricing()` explicitly calls the API with `product_id` — which it may or may not do depending on how it was implemented.

### Files Involved
- `static/js/app.js` — `saveWizardStep4()` (line 2547–2550) and `calculateWizardPricing()` (line 2491)
- `routers/pricing.py` — The `POST /api/pricing/calculate` endpoint already saves prices when `product_id` is supplied (line 186–208) — this is the correct pattern

### Recommended Fix
1. In `calculateWizardPricing()` (line 2491), ensure that the API call body includes `product_id: wizardProduct.id` (not `null`). This causes the backend to auto-save prices to the product record. Verify line 2491–2546 include `product_id` in the POST body.
2. If `product_id` is already included, `saveWizardStep4()` is already doing the right thing indirectly. If not, add it to the POST body in `calculateWizardPricing()`.
3. Update `saveWizardStep4()` to update `wizardProduct.amazon_price` etc. from the API response so that Step 5 preview has fresh data.

**Estimated effort: S (30–45 minutes)** — Read and patch `calculateWizardPricing()` body construction.

---

## R-12 — Step 5 export preview response parsing fragile

**Severity: Medium**

### Why It Matters
`loadWizardStep5Preview()` (line 2557) does `const rows = res.data || res`. The `api()` helper always returns the full `ApiResponse` object (`{success, message, data}`), so `res.data` will always be the correct accessor. The `|| res` fallback is dead code and could silently mask a broken response (if `res.data` is `undefined` due to an API error, the code would use the full `ApiResponse` object as the rows array — producing garbage in the table).

### Files Involved
- `static/js/app.js` — `loadWizardStep5Preview()` around line 2574: `const rows = res.data || res`

### Recommended Fix
1. Change `const rows = res.data || res` to `const rows = Array.isArray(res?.data) ? res.data : []`.
2. Add an else branch: if `rows.length === 0`, display a message "No preview data found. Complete Steps 1–4 first." with a "Go to Step 1" button.
3. Add error state rendering: wrap the `api()` call in try/catch and show `showToast('Preview failed: ' + err.message, 'error')` in the catch block, replacing the loading state with an error message.

**Estimated effort: XS (20 minutes)** — Defensive coding fix.

---

## R-13 — Vision auto-fill missing weight and HSN fields

**Severity: Medium**

### Why It Matters
`handleWizardImageUpload()` maps detected attributes to wizard form fields: name, brand, category, subcategory, notes. The Gemini Vision prompt returns a full JSON including inferred attributes. Weight (in grams) and HSN code are not auto-filled even though they appear in the `#w-weight` and `#w-hsn` form fields in Step 1. This is a minor usability gap — less manual data entry is always better.

### Files Involved
- `static/js/app.js` — `handleWizardImageUpload()` (line 2111) — the section that maps `result` fields to DOM inputs (approximately lines 2150–2200)

### Recommended Fix
The Gemini Vision prompt in `modules/vision_detector.py` (line 33) currently returns `product_type`, `suggested_name`, `category`, `subcategory`, `material`, `colors`, `key_features`, `suggested_keywords`, `confidence`. It does not return `weight_grams` or `hsn_code` because these cannot be reliably inferred from an image alone.

Two options:
1. **(Recommended)** Add `suggested_weight_grams` (optional, null if unknown) and `suggested_hsn_code` (optional) to the vision prompt's requested JSON schema in `_VISION_PROMPT`. Then in `handleWizardImageUpload()`, map `result.suggested_weight_grams` → `#w-weight` and `result.suggested_hsn_code` → `#w-hsn` if non-null.
2. **(Simpler)** Just add a note in the detected attributes display: "Weight and HSN code must be entered manually."

Option 1 is recommended — it improves automation with minimal risk since both fields are optional and the seller can override.

**Estimated effort: XS (25 minutes)** — One-line prompt extension + two-line DOM mapping.

---

## R-14 — Blanket `except Exception` in keyword_research.py

**Severity: Low**

### Why It Matters
`modules/keyword_research.py` uses multiple `except Exception` blocks that swallow all errors including `KeyboardInterrupt`, `SystemExit`, CAPTCHA blocks, network timeouts, and DOM structure changes. When scraping fails, the log shows a generic message rather than the specific cause. This makes debugging scraping regressions (e.g., if Amazon changes their DOM) very slow — the developer must add print statements rather than reading the logs.

### Files Involved
- `modules/keyword_research.py` — search for `except Exception` blocks (approximately 5–7 instances)

### Recommended Fix
Replace blanket catches with specific exception hierarchies:
1. `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout` → log with "Network error" category
2. `selenium.common.exceptions.TimeoutException`, `selenium.common.exceptions.NoSuchElementException` → log with "DOM structure error" category, include the selector name
3. `json.JSONDecodeError` → log with "Autocomplete parse error"
4. Retain one broad `except Exception` as the last resort at the outermost level only, with a `logger.exception()` call (not just `logger.warning()`) to capture the full traceback.

**Estimated effort: S (60 minutes)** — Careful but mechanical improvement.

---

## R-15 — `ContentValidationResult` model name mismatch

**Severity: Low**

### Why It Matters
CLAUDE.md and the implementation plan reference a `ContentValidationResult` model. The actual implementation uses `ContentValidationItem`. This is purely a naming inconsistency — the functionality is identical. However, if a future developer reads the plan and searches `models.py` for `ContentValidationResult`, they won't find it.

### Files Involved
- `models.py` — `ContentValidationItem` class (line ~332)
- `CLAUDE.md` — Phase 2 mention of `ContentValidationResult`
- `implementation_plan.md` — Phase 2 mention

### Recommended Fix
**Option A** (Recommended): Update `CLAUDE.md` Phase 2 model list to say `ContentValidationItem` (the implemented name). Keep the code as-is. Documents should reflect reality.  
**Option B**: Rename `ContentValidationItem` → `ContentValidationResult` in `models.py` and update all references in `routers/content.py`.

Prefer Option A — code is authoritative.

**Estimated effort: XS (10 minutes)** — Documentation update only.

---

## R-16 — Pricing engine inline in router (architecture violation)

**Severity: Low**

### Why It Matters
CLAUDE.md's architecture diagram lists `modules/pricing_engine.py` as a separate module under `modules/`. The actual pricing calculation functions (`_calculate_marketplace_pricing`, `_calculate_target_price`, helper functions `get_referral_fee_rate`, `get_closing_fee`, `get_shipping_fee`) are split between `config.py` (the fee lookups) and `routers/pricing.py` (the calculation logic). This violates the modules-vs-routers separation and makes `routers/pricing.py` a fat router — 286 lines, more business logic than routing.

### Files Involved
- `routers/pricing.py` — private functions `_calculate_marketplace_pricing()` and `_calculate_target_price()` (~lines 34–139)
- `modules/pricing_engine.py` — does not exist, should be created
- `config.py` — `get_referral_fee_rate()`, `get_closing_fee()`, `get_shipping_fee()` could stay in config (they're pure lookups) or move to pricing_engine

### Recommended Fix
Create `modules/pricing_engine.py` and move `_calculate_marketplace_pricing()` and `_calculate_target_price()` into it as public functions. Update `routers/pricing.py` to import from `modules.pricing_engine`. This is pure refactoring with no behaviour change.

**Do this last** — it touches working code and provides no user-visible improvement.

**Estimated effort: M (2 hours)** — Careful move + update all imports.

---

## R-17 — No automated test suite

**Severity: Low**

### Why It Matters
No `pytest` suite means regressions are caught only by manual testing. The project currently has `scratch/` test scripts, but these are one-off runners, not repeatable. With 7 routers and 4 modules, a formal test suite would prevent the kind of integration bugs found in this audit (R-01: settings bypass, R-03: wrong endpoint called).

### Files Involved
- `tests/` directory — does not exist, should be created
- Every router and module file is a candidate for unit/integration tests

### Recommended Fix
Create `tests/` with:
1. `tests/test_products.py` — CRUD endpoint tests using `httpx.AsyncClient` + `TestClient`
2. `tests/test_pricing.py` — verify fee calculation correctness for known inputs
3. `tests/test_content.py` — mock Gemini client, verify prompt construction and response parsing
4. `tests/test_keywords.py` — mock `requests.get`, verify NLP analysis outputs
5. `tests/conftest.py` — shared fixtures (test DB, mock settings)
6. Add `pytest`, `httpx`, `pytest-asyncio` to `requirements.txt`

**Estimated effort: XL (1–2 days)** — Low priority but high long-term value.

---

## Dependency Chain

```
R-02 (variations UI)
  └─► R-03 (wizard uses variations endpoint)
        └─► R-06 (per-variation tabs in step 3)

R-01 (settings wiring) — independent
R-04 (auto-price endpoint) — independent
R-05 (char counts in wizard) — independent
R-07 (mark as listed) — independent
R-08 (preview marketplace tabs) — independent
R-09 (content validation in wizard) — independent, but nicer after R-05
R-10 (Flipkart limit fix) — independent
R-11 (step 4 pricing persist) — independent
R-12 (step 5 response parsing) — independent
R-13 (vision weight/HSN) — independent
R-14 (except blocks) — independent
R-15 (model name docs) — independent
R-16 (pricing engine extract) — independent, do last
R-17 (test suite) — independent, do last
```
