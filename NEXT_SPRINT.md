# NEXT_SPRINT.md — Listing Helper v2.0 Remediation

> **Source audit**: `implementation_audit.md`
> **Source plan**: `remediation_plan.md`
> **Target**: Raise project completion 72% → 95%
> **Implementor**: Gemini
> **Rule**: Read `CLAUDE.md` and all source files referenced in each task before writing a single line of code.

---

## Execution Order

Tasks must be completed in this sequence.
Tasks with no listed dependency can be done in any order relative to each other.

```
[x] TASK-01  Fix Flipkart title char limit display             XS   no deps
TASK-02  Fix Step 5 preview response parsing               XS   no deps
TASK-03  Extend vision auto-fill (weight + HSN)            XS   no deps
TASK-04  Add /api/pricing/auto-price/{id} endpoint         S    no deps
TASK-05  Wire Settings UI to /api/settings                 M    no deps
TASK-06  Add char-count indicators to Wizard Step 3        S    no deps
TASK-07  Add content-validation gate at Step 3 exit        S    after TASK-06
TASK-08  Add "Mark as Listed" checkboxes to Step 5         S    no deps
TASK-09  Add marketplace filter tabs to Step 5 preview     M    no deps
TASK-10  Make saveWizardStep4 persist prices to DB         S    no deps
TASK-11  Add variation management UI to Wizard Step 1      L    no deps
TASK-12  Wire wizard content gen to generate-with-variations  S  after TASK-11
TASK-13  Add per-variation tabs to Wizard Step 3           L    after TASK-11, TASK-12
TASK-14  Improve exception specificity in keyword_research S    no deps
TASK-15  Extract modules/pricing_engine.py                 M    do last
```

> **Effort key**: XS < 30 min | S = 30–90 min | M = 2–4 hr | L = 4–8 hr

---

## TASK-01 — Fix Flipkart Title Character Limit Display

**Remediates**: R-10
**Severity**: Medium
**Effort**: XS
**Dependencies**: none
**Files**: `static/js/app.js`

### Problem
The standalone Content editor displays the Flipkart title counter as `0 / 100 chars`.
The correct limit per `CLAUDE.md`, `config.py` (`MARKETPLACE_LIMITS["flipkart"]["title_max_chars"]`),
and the Gemini prompt is **500 characters**.
Sellers unnecessarily truncate Flipkart titles because the UI lies about the limit.

### Exact Location
Search `app.js` for `0 / 100 chars` — appears near the Flipkart title counter div
inside `renderContentWorkspace()` or a similar render function around line 1012.
There are two places to fix:
1. The static counter label string displayed in the HTML template
2. The numeric `max` variable used in the counter update logic for the Flipkart title field

### What to Change
- Change the display string `0 / 100 chars` → `0 / 500 chars`
- Change the corresponding `max` variable from `100` → `500`
- The warning/danger threshold logic (`> max * 0.8` for warning, `> max` for danger) stays unchanged

### Acceptance Criteria
- [ ] Flipkart title counter shows `0 / 500 chars` when the field is empty
- [ ] Counter turns yellow (warning) at ~400 characters
- [ ] Counter turns red (danger) at >500 characters
- [ ] Amazon title counter still shows `0 / 200 chars` — not changed
- [ ] Meesho title counter still shows `0 / 200 chars` — not changed

### How to Test
1. `python main.py`
2. Navigate to Content page → open any product
3. Switch to the Flipkart tab in the content editor
4. Verify the title counter reads `0 / 500 chars`
5. Type 450 characters → verify warning (yellow) state
6. Type 510 characters → verify danger (red) state
7. Switch to Amazon tab → verify that counter still reads `0 / 200 chars`

---

## TASK-02 — Fix Wizard Step 5 Export Preview Response Parsing

**Remediates**: R-12
**Severity**: Medium
**Effort**: XS
**Dependencies**: none
**Files**: `static/js/app.js`

### Problem
`loadWizardStep5Preview()` (around line 2574) contains:

```
const rows = res.data || res;
```

The `api()` helper always returns the parsed `ApiResponse` object `{success, message, data}`.
The `|| res` fallback is dead code. If `res.data` is `undefined` (API error), the code silently passes
the full response object as the rows array, producing a broken table with no visible error.
There is also no try/catch around the API call — a network error crashes the function silently.

### Exact Location
`loadWizardStep5Preview()` — starts around line 2557 in `app.js`.
Target line is approximately 2574: `const rows = res.data || res`.

### What to Change
1. Replace `const rows = res.data || res` with a defensive accessor:
   - Use `res?.data` and validate it is an array before assigning
   - If the array is empty after a successful call, render a "no data" message in the table:
     `"No listing data found. Please complete Steps 1–4 before previewing."`
2. Wrap the entire `api()` call block in a `try/catch`:
   - In the `catch` block: set the table `thead` to an error row and call `showToast` with the error message
   - Do not leave the table in a loading spinner state on error

### Acceptance Criteria
- [ ] A product with fully generated content → Step 5 → preview table renders rows correctly
- [ ] A product with no generated content → Step 5 → "no data" message appears (not blank/broken)
- [ ] Simulating a network failure (stop the server mid-request) → `showToast` fires with an error message
- [ ] No uncaught JavaScript exceptions in the browser console for any of the above cases

### How to Test
1. Open wizard on a fresh product with no content → navigate directly to Step 5
2. Verify the "no data" message appears in the table
3. Generate content for a product → reach Step 5 normally → verify rows render
4. With server running, open Step 5 → then stop the server → click the tab again → verify error toast

---

## TASK-03 — Extend Vision Auto-Fill to Weight and HSN Fields

**Remediates**: R-13
**Severity**: Medium
**Effort**: XS
**Dependencies**: none
**Files**: `modules/vision_detector.py`, `static/js/app.js`

### Problem
The Gemini Vision prompt does not ask for product weight or HSN code.
The `handleWizardImageUpload()` function (around line 2111 in `app.js`) maps detected
attributes to wizard form fields but skips `#w-weight` and `#w-hsn` entirely.
Both fields are present in Wizard Step 1 and benefit from auto-fill when detectable.

### Part A — Update Vision Prompt
**File**: `modules/vision_detector.py` — `_VISION_PROMPT` constant (line 33)

Extend the requested JSON schema with two optional fields at the end of the object:
- `suggested_weight_grams` — estimated product weight in grams as a number, or `null` if not
  inferable from visible features like product size and material
- `suggested_hsn_code` — the Indian HSN classification code as a string (e.g., `"65050090"` for
  headgear, `"7323"` for kitchen articles), or `null` if not confident

The existing instruction "If you cannot determine something, use null" covers these new fields.
No other change to the prompt is needed.

### Part B — Map New Fields in JS
**File**: `static/js/app.js` — `handleWizardImageUpload()` (around line 2150–2200)

After the existing block that maps `result.suggested_name` → `#w-name`, `result.category` → `#w-category`, etc.:
- If `result.suggested_weight_grams` is a positive number: set `#w-weight` to that value
- If `result.suggested_hsn_code` is a non-empty string: set `#w-hsn` to that value
- Do not set the field to the string `"null"` — check that the value is genuinely present before assigning

### Acceptance Criteria
- [ ] Uploading a baseball cap image → `#w-weight` is auto-filled with a plausible gram value (e.g., 100–200)
- [ ] Uploading a baseball cap image → `#w-hsn` is auto-filled with a headgear HSN code (e.g., `65050090`) if the model is confident
- [ ] If Gemini returns `null` for either field → the form field stays empty (not the string `"null"`)
- [ ] All previously auto-filled fields (name, brand, category, subcategory, notes) continue to work

### How to Test
1. Ensure a valid Gemini API key is set (in `.env` or via Settings page)
2. Open wizard → drag a clear product image onto the dropzone
3. Wait for detection → verify `#w-weight` is populated with a number
4. Verify `#w-hsn` is populated with a code (or empty if Gemini returned null)
5. Manually edit either field → verify the pre-filled value is overwritable

---

## TASK-04 — Add `/api/pricing/auto-price/{product_id}` Endpoint

**Remediates**: R-04
**Severity**: Critical
**Effort**: S
**Dependencies**: none
**Files**: `routers/pricing.py`

### Problem
`CLAUDE.md` API endpoints table explicitly lists `POST /api/pricing/auto-price/{product_id}`.
It does not exist in `routers/pricing.py`. The router only has `/calculate` and `/calculate/batch`.
This endpoint is intended as a convenience route: given only a product ID, read cost/weight/category
from the DB automatically and compute prices — without the caller needing to supply product details.

### Context
The private functions `_calculate_marketplace_pricing()` and `_calculate_target_price()` already
exist in `routers/pricing.py`. The `get_product()` DB function is already imported at line 28.
The `save_pricing_snapshot()` and `update_product()` calls already exist in the `calculate()` route
and do exactly what is needed here.

### What to Add
Add a new route `POST /api/pricing/auto-price/{product_id}` to `routers/pricing.py`
after the existing `calculate/batch` route (after approximately line 255).

The route must:
1. Accept `product_id` as a path parameter (integer)
2. Accept two optional query parameters: `target_margin: float = 25.0` and `shipping_zone: str = "national"`
3. Call `await get_product(product_id)` — return HTTP 404 if the product does not exist
4. Extract `cost_price`, `weight_grams`, and `category` from the product dict
5. Return HTTP 400 if `cost_price` is None or zero, with message: `"Product has no cost price set. Update the product before auto-pricing."`
6. Call `_calculate_target_price()` and `_calculate_marketplace_pricing()` for all three marketplaces
   (same logic as in the `calculate()` route, reusing the existing private functions)
7. Call `save_pricing_snapshot()` for each marketplace and `update_product()` with the new prices
   and `listing_status: "priced"` (same as the `calculate()` route)
8. Return `ApiResponse` wrapping a `PricingResponse` object

No new Pydantic models are needed — the existing `PricingResponse` and `MarketplacePricing` cover the response.

### Acceptance Criteria
- [ ] `POST /api/pricing/auto-price/1` (valid product with cost price) returns `{success: true, data: {amazon: {...}, flipkart: {...}, meesho: {...}}}`
- [ ] `POST /api/pricing/auto-price/999` returns HTTP 404
- [ ] `POST /api/pricing/auto-price/1` for a product with no `cost_price` returns HTTP 400 with the specified message
- [ ] After the call, `SELECT amazon_price, flipkart_price, meesho_price, listing_status FROM products WHERE id=1` shows calculated values and `listing_status = 'priced'`
- [ ] After the call, `SELECT * FROM pricing_snapshots WHERE product_id=1` shows three new rows (one per marketplace)
- [ ] `GET /api/products/1` reflects the updated prices in the response

### How to Test
```
# Start server: python main.py

# Happy path
POST http://localhost:8000/api/pricing/auto-price/1

# 404 path
POST http://localhost:8000/api/pricing/auto-price/9999

# 400 path (product with null cost_price)
POST http://localhost:8000/api/pricing/auto-price/{id_with_no_cost}

# Verify DB
sqlite3 data/listing_helper.db "SELECT amazon_price, listing_status FROM products WHERE id=1;"
sqlite3 data/listing_helper.db "SELECT COUNT(*) FROM pricing_snapshots WHERE product_id=1;"
```

---

## TASK-05 — Wire Settings UI to `/api/settings` + Gemini Key Hot-Reload

**Remediates**: R-01
**Severity**: Critical
**Effort**: M
**Dependencies**: none
**Files**: `static/js/app.js`, `modules/content_generator.py`, `modules/vision_detector.py`

### Problem
The Settings page has two separate, competing implementations:
- **Correct path (already exists)**: `renderSettings()` calls `GET /api/settings` to populate the form.
  `saveDbSettings()` calls `PUT /api/settings/{key}` for each setting. Both functions are correct.
- **Dead path (the bug)**: The "Save Configurations" button inside `renderSettings()` calls
  `saveSettings()` (localStorage write, line 1566) instead of `saveDbSettings()`.
  `loadSettings()` (line 1579) reads from localStorage.

Additionally, `settings.GEMINI_API_KEY` is loaded once from `.env` at startup. A key saved to DB
via the UI has no effect on AI generation at runtime — the server never reads it.

### Part A — Fix the Save Button
**File**: `static/js/app.js` — inside the HTML template string in `renderSettings()` (around line 1528)

Change the "Save Configurations" button's `onclick` attribute from `saveSettings()` to `saveDbSettings()`.
This is a single string substitution in the template literal.

### Part B — Remove Dead localStorage Functions
**File**: `static/js/app.js`

Remove the entire `saveSettings()` function (lines 1566–1576) and the entire `loadSettings()` function
(lines 1579–1587).
Search the whole file for any remaining calls to `saveSettings()` or `loadSettings()` and remove those
call sites too (they may appear in `navigateTo()` or a page-init block).

### Part C — Gemini Key Hot-Reload from DB
**File**: `modules/content_generator.py` — `_call_gemini()` function (around line 386)

Currently the key check is:
```
if not settings.GEMINI_API_KEY:
    raise ValueError("Gemini API key not configured...")
```

Replace with a two-step lookup:
1. Check `settings.GEMINI_API_KEY` (env var, fast path)
2. If empty, `await` a call to `get_setting('gemini_api_key')` from the database
3. If still empty after both checks, raise the same `ValueError`
4. Use whichever key was found for the `genai.Client()` constructor

`get_setting` is already importable from `database`. Add the import at the top of `content_generator.py`.

Apply the same two-step lookup to `modules/vision_detector.py` — `detect_product_from_image()` has the
same API key guard pattern at the top of the function.

### Acceptance Criteria
- [ ] Settings page loads with values from the DB (check Network tab — `GET /api/settings` fires on navigation)
- [ ] Clicking "Save Configurations" fires `PUT /api/settings/gemini_api_key` etc. (check Network tab)
- [ ] After saving, `SELECT value FROM app_settings WHERE key='gemini_api_key'` shows the saved key in the DB
- [ ] `localStorage.getItem('listing_helper_settings')` returns `null` — nothing written to browser storage
- [ ] Removing `GEMINI_API_KEY` from `.env`, saving a key via the Settings UI, then generating content → generation succeeds using the DB key (server restart NOT required)
- [ ] The "Test Key Connection" button still works (calls `POST /api/settings/test-gemini`)
- [ ] No references to `saveSettings()` or `loadSettings()` remain in `app.js`

### How to Test
1. Remove `GEMINI_API_KEY` from `.env` (set it to empty string)
2. Restart the server: `python main.py`
3. Open Settings page
4. Enter a valid Gemini API key → click "Save Configurations"
5. Open DevTools → Application → Local Storage → verify no `listing_helper_settings` key exists
6. Navigate to a product → open wizard → reach Step 3 → click "Generate AI Copies"
7. Verify content is generated without error (proving the DB key was picked up)

---

## TASK-06 — Add Character Count Indicators to Wizard Step 3

**Remediates**: R-05
**Severity**: High
**Effort**: S
**Dependencies**: none
**Files**: `static/index.html`, `static/js/app.js`

### Problem
Wizard Step 3 (`#wcontent-3`) has plain `<input>` and `<textarea>` elements with no character counters.
The standalone Content editor already has `char-counter` CSS class, working counter divs, and a
`runLiveKeywordChecker()` update function. The CSS classes `.char-counter`, `.char-counter.warning`,
and `.char-counter.danger` already exist in `styles.css` and need no changes.

### Part A — Add Counter Divs to HTML
**File**: `static/index.html` — inside `#wcontent-3` (lines 339–391)

After each input or textarea in each marketplace column, add a counter div immediately below it.
Use this mapping of element ID → counter ID → character limit:

| Field ID | Counter ID | Limit | Unit |
|---|---|---|---|
| `w-amazon-title` | `wc-cnt-amazon-title` | 200 | chars |
| `w-amazon-bullets` | `wc-cnt-amazon-bullets` | 500 | chars per bullet |
| `w-amazon-desc` | `wc-cnt-amazon-desc` | 2000 | chars |
| `w-flipkart-title` | `wc-cnt-flipkart-title` | 500 | chars |
| `w-flipkart-features` | `wc-cnt-flipkart-features` | 200 | chars per feature |
| `w-flipkart-desc` | `wc-cnt-flipkart-desc` | 5000 | chars |
| `w-meesho-title` | `wc-cnt-meesho-title` | 200 | chars |
| `w-meesho-desc` | `wc-cnt-meesho-desc` | 2000 | chars |

Initial text for each: `"0 / {limit} {unit}"`.

### Part B — Attach Counter Logic in JS
**File**: `static/js/app.js`

Add a new function `attachWizardStep3Counters()`:
- For each of the 8 fields, attach an `input` event listener to the element
- On each input event, compute the current length and update the counter div text and CSS class
- For the two `textarea` fields that hold multiple items (bullets, features): measure the longest
  individual line (`value.split('\n').reduce(...)`) rather than total textarea length
- CSS classes to apply: none if at or below 80% of limit; `warning` if 80–100%; `danger` if over limit

Call `attachWizardStep3Counters()` from two places:
1. At the end of `loadWizardStep3Content()` (after fields are populated from the API response)
2. At the top of the `goToWizardStep(3)` branch (for when the user navigates back to Step 3)

After `startWizardContentGeneration()` programmatically sets field values (via `element.value = ...`),
the `input` event does not fire automatically. Dispatch a synthetic `input` event on each field after
population, or call a `refreshWizardStep3Counters()` helper that reads current values and updates all
counter divs in one pass.

### Acceptance Criteria
- [ ] All 8 counter divs are visible in Step 3 below their respective fields
- [ ] Typing in `#w-amazon-title` updates the Amazon title counter in real time
- [ ] After AI generation populates all fields, all 8 counters show the correct character counts (not `0`)
- [ ] Amazon title counter shows the correct warning/danger states at 161 chars and 201 chars respectively
- [ ] Flipkart title counter limit is 500 (consistent with TASK-01)
- [ ] Bullet counter reads the length of the longest individual bullet, not the total textarea text

### How to Test
1. Complete Steps 1–2 of the wizard for a product
2. Navigate to Step 3 → click "Generate AI Copies"
3. After generation, verify all counters show non-zero values immediately
4. Manually type in the Amazon title field past 160 chars → verify yellow warning
5. Continue past 200 chars → verify red danger

---

## TASK-07 — Add Content Validation Gate at Wizard Step 3 Exit

**Remediates**: R-09
**Severity**: High
**Effort**: S
**Dependencies**: TASK-06 (character counters should be visible first for coherence)
**Files**: `static/js/app.js`

### Problem
`saveWizardStep3()` (line 2447) saves content fields to the DB and advances the wizard.
It never calls `POST /api/content/validate` — so a seller can proceed to Step 4 with an
Amazon title that is 220 characters (20 over limit) with no warning. Validation only appears
in server logs, never in the UI.

### What to Change
**File**: `static/js/app.js` — `saveWizardStep3()` (line 2447)

At the beginning of `saveWizardStep3()`, before the product-update API call:

1. Build three validation payloads from the current field values in the wizard:
   - Amazon: `{ marketplace: 'amazon', title, bullets (as array), description }`
   - Flipkart: `{ marketplace: 'flipkart', title, bullets: features (as array), description }`
   - Meesho: `{ marketplace: 'meesho', title, description }`
2. Fire all three calls to `POST /api/content/validate` simultaneously using `Promise.all`
3. Collect every field where `is_valid === false` across all three responses
4. If violations exist:
   - Call `showToast` with a warning: `"⚠️ {N} field(s) exceed marketplace limits — review before exporting"`
   - Do **not** block the user — this is a warning only, not a hard gate
   - Log the specific violations to `console.warn` for debugging
5. If no violations: call `showToast("All marketplace fields are within limits ✓", "success")`
6. In both cases, continue to the update-product call and return `true`

### Acceptance Criteria
- [ ] With an oversized Amazon title (>200 chars) → "Next" shows a warning toast and still advances to Step 4
- [ ] With all fields within limits → a green "within limits" toast appears and wizard advances
- [ ] Three validation API calls fire in parallel (Network tab shows them starting within milliseconds)
- [ ] The toast message includes the count of violations (e.g., "2 field(s) exceed limits")
- [ ] Step 4 is reachable in both the warning and the all-valid case

### How to Test
1. Open wizard → reach Step 3 → manually type 250 characters in `#w-amazon-title`
2. Click "Next" (triggering `saveWizardStep3`)
3. Verify: a yellow warning toast appears AND Step 4 loads
4. Go back to Step 3 → shorten the title to 50 chars → click "Next"
5. Verify: a green success toast appears AND Step 4 loads

---

## TASK-08 — Add "Mark as Listed" Checkboxes to Wizard Step 5

**Remediates**: R-07
**Severity**: High
**Effort**: S
**Dependencies**: none
**Files**: `static/index.html`, `static/js/app.js`

### Problem
`CLAUDE.md` Phase 5 Step 5 requires: `"Mark as Listed checkbox per marketplace"`.
Without it, products remain in `"exported"` status permanently.
The Kanban board never shows them as `"listed"` and the seller loses tracking of which
marketplaces a listing has gone live on.
`ProductUpdate` model and `PUT /api/products/{id}` already accept `amazon_status`, `flipkart_status`,
`meesho_status` fields — no backend change needed.

### Part A — Add HTML
**File**: `static/index.html` — `#wcontent-5` (after the `.export-preview-table-container` div, around line 455)

Add a "Mark as Published" section containing:
- A small heading: "Mark as Published"
- A help text: "Check each marketplace where you have uploaded and published this listing."
- Three checkboxes with marketplace-coloured labels:
  - ID `w-listed-amazon` — "Listed on Amazon India"
  - ID `w-listed-flipkart` — "Listed on Flipkart"
  - ID `w-listed-meesho` — "Listed on Meesho"

### Part B — Wire to API in JS
**File**: `static/js/app.js` — `finishWizard()` (line 2612)

After the Excel blob download completes and before `closeWizard()`:
1. Read the three checkbox states
2. Build a `statusUpdate` object: for each checked marketplace, include `{amazon_status: 'listed'}` etc.
3. If at least one is checked: merge `statusUpdate` with `{listing_status: 'exported'}` into a single
   `PUT /api/products/{id}` call — set `listing_status: 'listed'` instead if all three are checked
4. If none are checked: only update `listing_status: 'exported'` as before

### Part C — Reset on Wizard Open
**File**: `static/js/app.js` — `openProductWizard()` (line 1883)

In the reset block at the top of `openProductWizard()`, set all three checkboxes (`w-listed-amazon`,
`w-listed-flipkart`, `w-listed-meesho`) to unchecked. Check for null before setting (the elements only
exist when Step 5 is rendered).

### Acceptance Criteria
- [ ] Three checkboxes are visible in Step 5 below the preview table
- [ ] Checking "Listed on Amazon India" and completing the wizard → `SELECT amazon_status FROM products WHERE id=X` returns `listed`
- [ ] Unchecked marketplaces retain their existing status (not forced to `listed`)
- [ ] Opening the wizard again on the same product → all three checkboxes start unchecked
- [ ] Kanban board on the Dashboard shows the product in its updated status after wizard close and page refresh

### How to Test
1. Complete the full wizard → reach Step 5 → check "Listed on Amazon India"
2. Click "Download & Finish"
3. Run: `sqlite3 data/listing_helper.db "SELECT amazon_status, flipkart_status FROM products WHERE id=1;"`
4. Verify: `listed|draft` (Amazon listed, Flipkart unchanged)
5. Navigate to Dashboard → verify Kanban board reflects the status

---

## TASK-09 — Add Marketplace Filter Tabs to Wizard Step 5 Preview

**Remediates**: R-08
**Severity**: High
**Effort**: M
**Dependencies**: none
**Files**: `static/index.html`, `static/js/app.js`, `static/css/styles.css`

### Problem
The Step 5 preview table shows all marketplace columns simultaneously — 30+ columns, unusable.
`CLAUDE.md` requires: `"Marketplace tabs (Amazon/Flipkart/Meesho/All)"`.
The `POST /templates/preview` endpoint already accepts a `marketplace` parameter that returns
only the relevant columns — no backend change needed.

### Part A — Add Tab Strip HTML
**File**: `static/index.html` — `#wcontent-5`, immediately before the `.export-preview-table-container` div (around line 446)

Add four tab buttons with IDs `w-ptab-all`, `w-ptab-amazon`, `w-ptab-flipkart`, `w-ptab-meesho`.
Each calls a JS function `switchPreviewTab('all'|'amazon'|'flipkart'|'meesho')`.
The "All" tab should be active by default. Amazon / Flipkart / Meesho tabs should use the
existing CSS variables `var(--amazon-color)`, `var(--flipkart-color)`, `var(--meesho-color)` for their text colour.

### Part B — Add JS State and Switch Function
**File**: `static/js/app.js` — global state section (near line 14, alongside `wizardStep`, `wizardProduct`)

Add: `let activePreviewMarketplace = 'all';`

Add function `switchPreviewTab(marketplace)`:
1. Set `activePreviewMarketplace = marketplace`
2. Remove `.active` class from all four `w-ptab-*` buttons; add `.active` to `w-ptab-{marketplace}`
3. Call `loadWizardStep5Preview()` to re-fetch with the updated filter

### Part C — Use the State Variable in the Preview Fetch
**File**: `static/js/app.js` — `loadWizardStep5Preview()` (around line 2569)

Change the POST body from `marketplace: 'all'` to `marketplace: activePreviewMarketplace`.

### Part D — Dynamic Column Headers in Table Render
**File**: `static/js/app.js` — the table-building section inside `loadWizardStep5Preview()`

When building the `<thead>`, derive which columns to show based on `activePreviewMarketplace`.
Define a column allowlist object keyed by marketplace:
- `all`: all keys present in the first row
- `amazon`: `['sku', 'name', 'brand', 'amazon_title', 'amazon_bullet_1'...'amazon_bullet_5', 'amazon_description', 'amazon_search_terms', 'amazon_price']`
- `flipkart`: `['sku', 'name', 'brand', 'flipkart_title', 'flipkart_key_feature_1'...'flipkart_key_feature_6', 'flipkart_description', 'flipkart_keywords', 'flipkart_price']`
- `meesho`: `['sku', 'name', 'brand', 'meesho_title', 'meesho_description', 'meesho_price']`

When rendering table rows, only write cells for the columns in the current allowlist.

### Part E — Reset State on Wizard Open
**File**: `static/js/app.js` — `openProductWizard()` and `goToWizardStep(5)`

Reset `activePreviewMarketplace = 'all'` and reset the active tab styling to `w-ptab-all`.

### Part F — CSS
**File**: `static/css/styles.css`

Add `.preview-tab-strip` (horizontal flex row, small gap, margin-bottom before the table)
and `.preview-tab` (small pill button with transparent background and border).
Add `.preview-tab.active` with bottom border using `var(--accent-primary)` or marketplace colour.
These should feel visually consistent with the existing `.tab` pattern used elsewhere in the app.

### Acceptance Criteria
- [ ] Step 5 shows four tabs: All / Amazon / Flipkart / Meesho
- [ ] Clicking "Amazon" tab → table shows only Amazon-relevant columns
- [ ] Clicking "All" tab → table shows all columns
- [ ] Each tab switch triggers a new `POST /templates/preview` request (visible in Network tab with correct `marketplace` value)
- [ ] Active tab is visually distinct from inactive tabs
- [ ] Tab state resets to "All" each time the wizard is opened

### How to Test
1. Complete full wizard for a product with content → reach Step 5
2. Verify four tabs are present above the table
3. Click "Amazon" → verify only Amazon columns shown (~10 columns, not 30)
4. Click "Flipkart" → verify only Flipkart columns shown
5. Click "All" → verify all columns shown
6. Close and reopen wizard → verify "All" tab is active by default

---

## TASK-10 — Make `saveWizardStep4()` Persist Prices to DB

**Remediates**: R-11
**Severity**: Medium
**Effort**: S
**Dependencies**: none
**Files**: `static/js/app.js`

### Problem
`saveWizardStep4()` (line 2547) is:
```javascript
async function saveWizardStep4() {
  await calculateWizardPricing();
  return true;
}
```
Whether prices are actually saved to the DB depends on whether `calculateWizardPricing()` includes
`product_id` in its POST body to `/pricing/calculate`. If `product_id` is missing, prices live only
in the JS variable `wizardPricingResult` and are lost when the modal closes without finishing.

### What to Verify and Fix
**File**: `static/js/app.js` — `calculateWizardPricing()` (line 2491)

1. Read the full body of `calculateWizardPricing()` and locate the `api('/pricing/calculate', 'POST', {...})` call
2. Verify the POST body includes `product_id: wizardProduct?.id`
3. If `product_id` is absent: add it to the POST body
4. After the API call, the response contains `{amazon: {selling_price}, flipkart: {selling_price}, meesho: {selling_price}}` — update the local `wizardProduct` object with these prices so Step 5 preview has current data without a re-fetch

### Acceptance Criteria
- [ ] After clicking "Next" from Step 4, `SELECT amazon_price, listing_status FROM products WHERE id=X` shows calculated values and `listing_status = 'priced'`
- [ ] If the wizard is closed after Step 4 and reopened on the same product, the pricing cards in Step 4 show the previously calculated prices (loaded from the product record)
- [ ] Closing the wizard without reaching Step 5 does not lose the pricing data

### How to Test
```
# Before running wizard through Step 4
sqlite3 data/listing_helper.db "SELECT amazon_price, listing_status FROM products WHERE id=1;"
# Expected: amazon_price = NULL

# Complete Steps 1-4 of the wizard, click Next after Step 4

sqlite3 data/listing_helper.db "SELECT amazon_price, listing_status FROM products WHERE id=1;"
# Expected: amazon_price = some value, listing_status = priced
```

---

## TASK-11 — Add Variation Management UI to Wizard Step 1

**Remediates**: R-02
**Severity**: Critical
**Effort**: L
**Dependencies**: none
**Files**: `static/index.html`, `static/js/app.js`, `static/css/styles.css`

### Problem
`CLAUDE.md` Phase 5 Step 1 requires: `"Add variations (color/size SKUs)"`.
Wizard Step 1 has no UI for this. Without it, the variation-aware content generation backend
(TASK-12) cannot be triggered, and multi-SKU products (e.g., a cap in 5 colours) must use the
standalone product modal to add variations — breaking the guided wizard flow.
All backend APIs are already implemented: `POST /api/products/{id}/variations`,
`GET /api/products/{id}/variations`, `DELETE /api/products/{id}/variations/{var_id}`.

### Part A — Add Variation Section to HTML
**File**: `static/index.html` — `#wcontent-1`, after the right-panel manual details form grid,
before the closing `</div>` of the right panel (after approximately line 302)

Add a "Variations" section containing:
- A heading: "Variations (Optional)"
- Helper text: "Add color, size, or material variants. Each variation gets its own SKU and tailored AI content."
- A container `id="w-variations-list"` — initially empty, populated by JS
- A button labelled "＋ Add Variation" that calls `addWizardVariation()`

Each variation row injected into `#w-variations-list` by JS must contain:
- A `<select>` for `variation_type` with options: Color, Size, Material, Style, Other
- A text `<input>` for `variation_value` with placeholder `"e.g. Black, XL, Cotton"`
- A text `<input>` for `variation_sku` with placeholder `"e.g. BC-BLK-001"`
- A remove button labelled `"✕"` that calls `removeWizardVariation(this.closest('.w-var-row'))`
- A `data-var-id` attribute on the row element: empty string for new rows, the DB integer ID for existing ones

### Part B — JS: Add, Remove, Read Functions
**File**: `static/js/app.js`

Add module-level state at the top of the file (alongside `wizardStep`, `wizardProduct`):
```
let wizardVariations = [];
```

Add these three functions:

**`addWizardVariation(varType='', varValue='', varSku='', varId='')`**:
- Creates and appends a new `.w-var-row` element to `#w-variations-list`
- Fills the type, value, SKU fields and the `data-var-id` attribute from the parameters
- Returns the new row element

**`removeWizardVariation(rowEl)`**:
- Removes `rowEl` from the DOM

**`getWizardVariations()`**:
- Reads all `.w-var-row` elements from `#w-variations-list`
- Returns an array of objects: `{var_id, variation_type, variation_value, sku}`
- Skips rows where `variation_value` or `sku` is empty

### Part C — JS: Load Existing Variations on Wizard Open
**File**: `static/js/app.js` — `openProductWizard()` (line 1883)

When `productOrId` is provided (editing an existing product), after loading the product fields
(around line 1919), also:
1. Clear `#w-variations-list`
2. Set `wizardVariations = []`
3. Call `GET /api/products/{id}/variations`
4. For each returned variation, call `addWizardVariation(v.variation_type, v.variation_value, v.sku, v.id)`

When no `productOrId` is provided (new product), clear `#w-variations-list` and reset `wizardVariations = []`.

### Part D — JS: Sync Variations in saveWizardStep1()
**File**: `static/js/app.js` — `saveWizardStep1()` (line 2209)

After the product create-or-update API call resolves and `wizardProduct` is set:
1. Call `getWizardVariations()` to get the current rows
2. For each row with an empty `var_id` (new variation): call `POST /api/products/{id}/variations`
   with `{variation_type, variation_value, sku, additional_cost: 0, stock_quantity: 0}`
3. Store the returned variation record (including its DB `id`) back into the row's `data-var-id` attribute
4. After all new variations are saved, call `GET /api/products/{id}/variations` to get the complete
   current list and set `wizardVariations = response.data` (full variation records)

### Part E — CSS
**File**: `static/css/styles.css`

Add:
- `.wizard-variations-section` — a container with a subtle top border and vertical padding
- `.w-var-row` — flex row with small gap, aligning the select, two inputs, and remove button
- The remove button should use `var(--accent-danger)` for its colour

### Acceptance Criteria
- [ ] Step 1 shows a "Variations" section below the manual details form
- [ ] "＋ Add Variation" appends a new row with a type dropdown, value input, SKU input, and remove button
- [ ] Clicking "✕" removes the row
- [ ] After clicking "Next" from Step 1, the new variations appear in the DB:
  `GET /api/products/{id}/variations` returns the added variations
- [ ] Opening wizard on an existing product with variations pre-populates the variation rows
- [ ] Rows with empty `variation_value` or `sku` are ignored (not sent to the API)
- [ ] `wizardVariations` is populated after Step 1 completes, available for TASK-12

### How to Test
1. Open wizard → Step 1 → fill product details
2. Click "＋ Add Variation" twice → fill: "Color / Black / BC-BLK-001" and "Color / Red / BC-RED-001"
3. Click "Next"
4. `GET http://localhost:8000/api/products/{id}/variations` → verify 2 variations returned
5. Close wizard → reopen on same product → verify 2 variation rows pre-populated
6. Add a third row but leave fields empty → click "Next" → verify only 2 variations in API (empty row ignored)

---

## TASK-12 — Wire Wizard Content Generation to `/generate-with-variations`

**Remediates**: R-03
**Severity**: Critical
**Effort**: S
**Dependencies**: TASK-11 (requires `wizardVariations` state variable)
**Files**: `static/js/app.js`

### Problem
`startWizardContentGeneration()` (line 2411) calls `POST /api/content/generate`.
This generates content for the base product only.
`POST /api/content/generate-with-variations` — which generates tailored content per variation and saves
to the `variation_content` table — is fully implemented but never called from the wizard.
The variation-aware backend is dead code in the wizard flow.

### Exact Location
`startWizardContentGeneration()` — line 2430:
```javascript
await api('/content/generate', 'POST', {
  product_id: wizardProduct.id,
  marketplace: 'all'
});
```

### What to Change
**File**: `static/js/app.js` — replace the hardcoded call at line 2430

Before calling the API, collect the currently selected keywords:
- Read all elements matching `.kw-pill.selected` (or whatever class marks a selected pill) in `#w-pills-primary` and `#w-pills-secondary`
- Extract the keyword text from each element's `textContent` or `data-keyword` attribute
- Store as `selectedKeywords` array

Then apply a conditional:
- If `wizardVariations.length > 0`: call `POST /api/content/generate-with-variations` with `{product_id: wizardProduct.id, keywords: selectedKeywords}`
  - Update the overlay text to: `"Gemini AI is generating listings for base product + N variations..."`
- If `wizardVariations.length === 0`: call `POST /api/content/generate` with `{product_id: wizardProduct.id, marketplace: 'all', keywords: selectedKeywords}`

In both cases, after success: call `loadWizardStep3Content()` as currently done.

### Acceptance Criteria
- [ ] Product with 0 variations → Network tab shows call to `/content/generate`
- [ ] Product with 2 variations → Network tab shows call to `/content/generate-with-variations`
- [ ] Overlay text shows variation count when applicable: `"...base product + 2 variations..."`
- [ ] After generation with variations, `variation_content` table has rows:
  `sqlite3 data/listing_helper.db "SELECT COUNT(*) FROM variation_content;"`
- [ ] Keywords selected in Step 2 are present in the request body (check Network tab → Request Payload)
- [ ] Step 3 editor fields populate with base product content in both cases

### How to Test
1. Create a product with 2 variations (requires TASK-11)
2. Open wizard → complete Step 1 (with 2 variations) → Step 2 (run keywords, select some) → Step 3
3. Click "Generate AI Copies"
4. DevTools → Network → verify POST to `/api/content/generate-with-variations`
5. `sqlite3 data/listing_helper.db "SELECT variation_id, marketplace FROM variation_content;"`
6. Verify rows exist for each variation × each marketplace

---

## TASK-13 — Add Per-Variation Tabs to Wizard Step 3

**Remediates**: R-06
**Severity**: High
**Effort**: L
**Dependencies**: TASK-11 and TASK-12
**Files**: `static/index.html`, `static/js/app.js`, `routers/content.py`, `database.py`, `static/css/styles.css`

### Problem
After TASK-12, variation content exists in the DB. But Step 3 only shows base product content in the
three-column editor. The seller cannot review or edit the per-variation titles and descriptions.
`CLAUDE.md` requires: `"Per-variation tabs"`.

### Part A — Add Tab Container to HTML
**File**: `static/index.html` — `#wcontent-3` header row (around line 340–345)

Replace the current heading-only row with a flex row containing:
- The existing `<h4>` heading on the left
- A tab container `id="w-variation-tabs"` in the middle (populated by JS)
- The existing "Generate AI Copies" button on the right

### Part B — Backend: Add Variation Content Fetch Endpoint
**File**: `database.py`

Add async function `get_variation_content_for_variation(variation_id: int) -> list[dict]`:
- Query `SELECT * FROM variation_content WHERE variation_id = ?`
- Return all rows as a list of dicts (one row per marketplace)

**File**: `routers/content.py`

Add route `GET /api/content/variation/{variation_id}`:
- Call the new DB function
- Return `ApiResponse` with the list of variation content rows in `data`

### Part C — Tab Rendering in JS
**File**: `static/js/app.js` — `loadWizardStep3Content()` (line 2386)

Add module-level state: `let activeStep3VariationId = null;` (null = base product)

After populating the base product content fields, also:
1. Clear `#w-variation-tabs`
2. If `wizardVariations.length > 0`:
   - Inject a "Base Product" tab button (active by default) that calls `switchStep3Tab(null)`
   - For each variation in `wizardVariations`, inject a tab button labelled with `variation.variation_value`
     that calls `switchStep3Tab(variation.id)`
3. If `wizardVariations.length === 0`: leave `#w-variation-tabs` empty (no tabs shown)

### Part D — Tab Switch Function
**File**: `static/js/app.js`

Add function `switchStep3Tab(variationId)`:
1. Set `activeStep3VariationId = variationId`
2. Update tab button active states (remove `.active` from all, add to the clicked one)
3. If `variationId === null`: load base product content into editor fields (re-call `loadWizardStep3Content()` or just re-populate from `wizardProduct`)
4. If `variationId !== null`:
   - Call `GET /api/content/variation/{variationId}` (the new endpoint from Part B)
   - Find the row for each marketplace in the response
   - Populate the editor fields with the variation's content
   - Trigger counter refresh (from TASK-06) after populating

### Part E — Save Tab Edits
**File**: `static/js/app.js` — `saveWizardStep3()` (line 2447)

For v1: only save base product edits (existing behaviour).
For variation tab edits: they are advisory — variation content can be regenerated.
Add a comment: `// TODO: Save variation tab edits to variation_content table in v2`.
This is an accepted known limitation documented in code.

### Part F — Reset on Wizard Open
**File**: `static/js/app.js` — `openProductWizard()` and `goToWizardStep(3)`

Reset `activeStep3VariationId = null` and clear `#w-variation-tabs`.

### Part G — CSS
**File**: `static/css/styles.css`

Add `.wizard-variation-tabs` (horizontal flex, small gap), `.wizard-var-tab` (small pill button),
`.wizard-var-tab.active` (highlighted accent background).

### Acceptance Criteria
- [ ] Product with 0 variations → no tab strip shown, editor works as before
- [ ] Product with 2 variations → three tabs shown: "Base Product", "Black", "Red"
- [ ] Clicking "Black" tab → editor fields populate with the Black variation's content
- [ ] Clicking "Base Product" tab → editor fields return to base product content
- [ ] All 8 character counters (from TASK-06) update correctly when switching tabs
- [ ] Clicking "Generate AI Copies" regenerates all content and refreshes the active tab

### How to Test
1. Create a product with 2 color variations → complete Steps 1–2 → reach Step 3
2. Click "Generate AI Copies"
3. After generation, verify 3 tabs appear: "Base Product", "Black", "Red"
4. Click "Black" tab → verify Amazon title contains "Black" in it
5. Click "Base Product" tab → verify generic title is shown
6. `sqlite3 data/listing_helper.db "SELECT title, marketplace FROM variation_content WHERE variation_id=1;"`
7. Verify rows for amazon, flipkart, meesho

---

## TASK-14 — Improve Exception Specificity in `keyword_research.py`

**Remediates**: R-14
**Severity**: Low
**Effort**: S
**Dependencies**: none
**Files**: `modules/keyword_research.py`

### Problem
Multiple `except Exception` blocks in `keyword_research.py` swallow all errors (CAPTCHA responses,
DOM changes, network timeouts, `KeyboardInterrupt`) as generic log warnings.
When scraping fails, the log shows a vague message rather than the specific cause.
Debugging Amazon DOM changes or connection failures requires adding print statements rather than
reading the logs.

### What to Change
**File**: `modules/keyword_research.py`

1. Find every `except Exception` block in the file (approximately 5–7 instances)
2. For each block, replace with the most specific exception type(s) applicable:
   - Network failures → `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout`, `requests.exceptions.HTTPError`
   - Selenium failures → `selenium.common.exceptions.TimeoutException`, `selenium.common.exceptions.NoSuchElementException`, `selenium.common.exceptions.StaleElementReferenceException`, `selenium.common.exceptions.WebDriverException`
   - JSON parse errors → `json.JSONDecodeError`
3. Add a brief comment above each `except` clause explaining what specific scenario it handles
4. For the single outermost catch-all that must remain broad: change `logger.warning(...)` to `logger.exception(...)`. The `exception()` call automatically includes the full stack trace in the log output — `warning()` does not
5. Never catch `KeyboardInterrupt`, `SystemExit`, or `GeneratorExit` — let these propagate

### Acceptance Criteria
- [ ] No bare `except Exception:` blocks remain except the single outermost catch-all
- [ ] Each specific `except` clause has a comment explaining the scenario
- [ ] The outermost catch-all uses `logger.exception()` (not `logger.warning()`)
- [ ] Running `python main.py` produces no import errors
- [ ] The server still starts and keyword research still functions (no broken imports from adding `requests.exceptions` or `selenium.common.exceptions`)

### How to Test
1. Start the server: `python main.py`
2. POST to `/api/keywords/research` with `{"seed_keywords": ["test"], "url": "https://invalid-domain-xyz.com"}`
3. Check the server console log — verify the error clearly identifies the failure type (e.g., `ConnectionError`, `Timeout`) rather than just "Scraping failed"
4. Verify the server remains running after the failed request (exception was caught properly)

---

## TASK-15 — Extract `modules/pricing_engine.py` Module

**Remediates**: R-16
**Severity**: Low
**Effort**: M
**Dependencies**: none — **perform this task last**
**Files**: `modules/pricing_engine.py` (new), `routers/pricing.py`

### Problem
`CLAUDE.md` architecture diagram lists `modules/pricing_engine.py` as a separate module.
The private calculation functions `_calculate_marketplace_pricing()` and `_calculate_target_price()`
live inside `routers/pricing.py`, making it a 286-line fat router that mixes business logic
with HTTP handling.
This is a pure refactoring task — **zero behaviour change**.

### What to Create
**File**: `modules/pricing_engine.py` (new file)

Move the following from `routers/pricing.py` into this file as public functions:
- `_calculate_marketplace_pricing()` → rename to `calculate_marketplace_pricing()` (remove leading underscore)
- `_calculate_target_price()` → rename to `calculate_target_price()` (remove leading underscore)

The fee lookup functions `get_referral_fee_rate()`, `get_closing_fee()`, `get_shipping_fee()` stay in
`config.py` — they are configuration lookups, not engine logic. Import them in `pricing_engine.py`.

Add a module docstring: `"""Pricing engine — fee calculation and margin optimisation for Indian marketplaces."""`

**File**: `routers/pricing.py`

- Delete the two moved function definitions
- Add at the top: `from modules.pricing_engine import calculate_marketplace_pricing, calculate_target_price`
- Update every internal call site: remove the leading underscore prefix from both function names

### Acceptance Criteria
- [ ] `modules/pricing_engine.py` exists and contains both functions (without underscore prefix)
- [ ] `routers/pricing.py` no longer contains either function definition
- [ ] `python main.py` starts without any import errors
- [ ] `POST /api/pricing/calculate` returns identical results as before this task
- [ ] `POST /api/pricing/auto-price/{id}` (from TASK-04) still works correctly
- [ ] No other file in the project imports the old underscore-prefixed names

### How to Test
```
python main.py
# Verify no errors in console

# Run the same pricing request as before this task
POST http://localhost:8000/api/pricing/calculate
Body: {"cost_price": 150, "weight_grams": 200, "target_margin": 25, "shipping_zone": "national"}

# Compare response to a baseline taken before this task — must be identical
```

---

## Summary Table

| Task | Remediates | Severity | Effort | Key Files | Deps |
|---|---|---|---|---|---|
| TASK-01 | R-10 Flipkart limit | Medium | XS | app.js | — |
| TASK-02 | R-12 Preview parsing | Medium | XS | app.js | — |
| TASK-03 | R-13 Vision fields | Medium | XS | vision_detector.py, app.js | — |
| TASK-04 | R-04 auto-price endpoint | Critical | S | pricing.py | — |
| TASK-05 | R-01 Settings wiring | Critical | M | app.js, content_generator.py | — |
| TASK-06 | R-05 Step 3 char counts | High | S | index.html, app.js | — |
| TASK-07 | R-09 Validation gate | High | S | app.js | TASK-06 |
| TASK-08 | R-07 Mark as Listed | High | S | index.html, app.js | — |
| TASK-09 | R-08 Preview tabs | High | M | index.html, app.js, styles.css | — |
| TASK-10 | R-11 Step 4 persist | Medium | S | app.js | — |
| TASK-11 | R-02 Variation UI | Critical | L | index.html, app.js, styles.css | — |
| TASK-12 | R-03 Variation gen | Critical | S | app.js | TASK-11 |
| TASK-13 | R-06 Variation tabs | High | L | index.html, app.js, content.py, database.py, styles.css | TASK-11, TASK-12 |
| TASK-14 | R-14 Exception types | Low | S | keyword_research.py | — |
| TASK-15 | R-16 pricing_engine.py | Low | M | pricing_engine.py (new), pricing.py | do last |

**Total estimated effort**: 28–34 hours
**Projected completion after sprint**: 94–96%

**Intentionally deferred**:
- R-15: Model naming doc fix — update CLAUDE.md in any future doc-cleanup pass
- R-17: Automated test suite — schedule as a separate testing sprint
