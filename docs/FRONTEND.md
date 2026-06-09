# Frontend

The frontend is a vanilla JavaScript Single-Page Application (SPA). There is no framework,
no TypeScript, no build tool, and no bundler. All logic lives in three files:

| File | Size | Purpose |
|---|---|---|
| `static/index.html` | ~200 lines | HTML shell, wizard markup, modal containers |
| `static/css/styles.css` | ~1800 lines | Glassmorphism dark theme |
| `static/js/app.js` | ~2500 lines | All SPA logic |

---

## Page Structure

Three top-level pages, rendered into `#main-content`:

| Page | Render Function | URL Hash |
|---|---|---|
| Dashboard | `renderDashboard()` | `#dashboard` |
| Products | `renderProducts()` | `#products` |
| Settings | `renderSettings()` | `#settings` |

Navigation is handled by `navigateTo(page)`:
```js
function navigateTo(page) {
  const allowed = ['dashboard', 'products', 'settings'];
  if (!allowed.includes(page)) page = 'dashboard';
  currentPage = page;
  window.location.hash = page;
  renderPage();
}
```

Hash changes trigger `navigateTo` via a `hashchange` listener on `window`. The initial
page on load is derived from `window.location.hash` or defaults to `dashboard`.

---

## Component Hierarchy

```
index.html
├── #nav-bar               — top navigation bar
│     ├── .nav-logo
│     └── .nav-links       — Dashboard / Products / Settings
│
├── #main-content          — page content area (swapped by navigateTo)
│     ├── renderDashboard()
│     │     ├── .stats-grid   — total counts (total / draft / ready / listed)
│     │     └── .kanban-board — 6 columns (new/keywords_done/content_ready/priced/exported/listed)
│     │           └── .kanban-column > .product-card (draggable)
│     │
│     ├── renderProducts()
│     │     ├── .filter-bar   — category, marketplace status, search, per-page
│     │     ├── .products-grid > .product-card
│     │     └── .pagination-controls
│     │
│     └── renderSettings()
│           ├── .settings-section  — Gemini API Key
│           ├── .settings-section  — Scraper Config
│           └── .settings-section  — Pricing Defaults
│
└── #wizard-overlay        — fixed full-screen modal (displayed on top of any page)
      ├── .wizard-header   — step breadcrumbs (1–5) + close button
      └── .wizard-body     — step-specific content
            ├── Step 1: #wizard-step-1  — product form + variation table + image dropzone
            ├── Step 2: #wizard-step-2  — keyword seed input + progress bar + results grid
            ├── Step 3: #wizard-step-3  — marketplace tabs (Amazon/Flipkart/Meesho) + editor
            ├── Step 4: #wizard-step-4  — pricing cards + margin slider
            └── Step 5: #wizard-step-5  — preview table + marketplace filter tabs + download button
```

---

## Wizard Architecture

### Lifecycle

```
openWizard(productId?)
    │  Clears all wizard state globals
    │  Shows #wizard-overlay
    │  If productId: loads product + variations from API
    └─► goToWizardStep(1)

goToWizardStep(n)
    │  Hides all step panels
    │  Shows #wizard-step-{n}
    │  Calls step entry handler (loadWizardStep2Content, etc.)
    └─► Updates step indicator breadcrumbs

[User clicks "Next"]
    │  Calls saveWizardStep{n}()
    │     Returns true  → goToWizardStep(n+1)
    │     Returns false → stay on step, show error toast

finishWizard()
    │  POST /api/templates/export
    │  Triggers browser download
    └─► closeWizard()

closeWizard()
    │  Hides #wizard-overlay
    └─► Clears wizard state
```

### Step Entry Handlers

| Step | Entry Handler | Auto-triggered? |
|---|---|---|
| 1 | `loadWizardStep1(productId?)` | On wizard open |
| 2 | `loadWizardStep2Content()` | On step 2 enter |
| 3 | `loadWizardStep3Content()` | On step 3 enter |
| 4 | `calculateWizardPricing()` | On step 4 enter |
| 5 | `loadWizardStep5Preview()` | On step 5 enter |

Steps 3, 4, and 5 auto-fire their API calls when the step becomes active so the user
immediately sees results rather than having to click a button.

---

## State Management

All wizard state is module-level globals in `app.js`. State is cleared when the wizard
opens or closes.

```js
// Wizard globals
let wizardStep = 1;
let wizardProduct = null;       // full product object from DB
let wizardVariations = [];      // array of variation objects
let wizardStep3ActiveTab = 'base';
let wizardStep3Data = {         // in-memory content (not yet saved to DB)
  base: { amazon: null, flipkart: null, meesho: null },
  variations: {}                // keyed by variation id
};
let wizardPricingResult = null; // last PricingResponse from API
let activePreviewMarketplace = 'all';

// Non-wizard page globals
let currentPage = 'dashboard';
let productListPage = 1;
let productListFilters = { category: '', status: '', search: '', per_page: 50 };
let keywordResearchEventSource = null; // active SSE connection
```

`wizardStep3Data` is a write-through cache. Content is modified in memory as the user
edits fields inline. On "Next" from Step 3, the in-memory content is flushed to the
API via `PUT /api/products/{id}`.

---

## API Communication

All HTTP requests use the `api()` helper:

```js
async function api(path, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : null
  };
  const res = await fetch('/api' + path, opts);
  const json = await res.json();
  if (!json.success) throw new Error(json.message || 'API error');
  return json;  // caller reads json.data
}
```

Callers always access the payload via `res.data`. On error, the helper throws, and
callers catch to show a toast notification.

---

## SSE Handling (Keyword Research)

```js
function startKeywordResearch(seed, limit, productId) {
  const url = `/api/keywords/research/stream?seed=...`;
  keywordResearchEventSource = new EventSource(url);

  keywordResearchEventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.step === 'complete') {
      keywordResearchEventSource.close();
      if (!data.results) {
        console.warn('[keyword-research] complete event missing results — ignoring');
        return;
      }
      renderWizardKeywordResults(data.results);
      return;
    }

    if (data.step === 'error') {
      keywordResearchEventSource.close();
      showToast(data.message, 'error');
      return;
    }

    // Progress update
    updateKeywordProgressBar(data.current, data.total, data.message);
  };

  keywordResearchEventSource.onerror = () => {
    keywordResearchEventSource.close();
    showToast('Keyword research connection lost', 'error');
  };
}
```

The `EventSource` connection is stored in `keywordResearchEventSource` so it can be
explicitly closed on wizard close or page navigation.

---

## Rendering Patterns

### `renderDashboard()`

Fetches `GET /api/products/stats/overview` to populate stat cards.
Fetches `GET /api/products/?per_page=200` to populate the Kanban board.

Kanban cards are draggable (`draggable="true"`). Drop handlers call
`PUT /api/products/{id}` with the new `listing_status`.

### `renderProducts()`

Fetches `GET /api/products/` with current `productListFilters`. Renders a card grid.
Each card has Edit (opens wizard) and Delete buttons.
Filter bar changes immediately re-fetch (debounced 300ms on text search).

### `renderSettings()`

Fetches `GET /api/settings/`. Renders a form. On submit, calls
`PUT /api/settings/{key}?value=...` for each changed key.
"Test API Key" button calls `POST /api/settings/test-gemini`.

### `renderWizardKeywordResults(results)`

Renders keyword pills from `results.primary` (checkboxes, pre-checked).
Renders secondary, long-tail, and autocomplete keywords as lists.

Null-guard at function entry:
```js
if (!results) {
  console.warn('[renderWizardKeywordResults] called with null/undefined results');
  pillsPrimary.innerHTML = '<span class="text-muted">No keyword data available.</span>';
  return;
}
```

---

## UI Design System

### Theme

Glassmorphism dark theme. Key CSS variables (defined on `:root`):

| Variable | Value | Usage |
|---|---|---|
| `--bg-primary` | `#0f0f1a` | Page background |
| `--bg-card` | `rgba(255,255,255,0.05)` | Card backgrounds |
| `--border-color` | `rgba(255,255,255,0.1)` | Card borders |
| `--accent-primary` | `#6c63ff` | Buttons, links |
| `--text-primary` | `#e0e0e0` | Body text |
| `--text-muted` | `#888` | Secondary text |
| `--success` | `#4caf50` | Success states |
| `--warning` | `#ff9800` | Warning states |
| `--error` | `#f44336` | Error states |

### Cards

All content surfaces use `.card`:
```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  padding: 1.5rem;
}
```

### Toast Notifications

```js
function showToast(message, type = 'info') {
  // type: 'info' | 'success' | 'warning' | 'error'
  // Renders a floating toast, auto-dismisses after 4s
}
```

### Character Counters

Step 3 content fields render live character counters. Counter is green when within
limit, red when over:
```js
function updateCharCounter(inputEl, limit) {
  const count = inputEl.value.length;
  counterEl.textContent = `${count} / ${limit}`;
  counterEl.classList.toggle('over-limit', count > limit);
}
```

### Marketplace Colours

| Marketplace | Hex | Usage |
|---|---|---|
| Amazon | `#FF9900` | Step 3 tab, header accent |
| Flipkart | `#2874F0` | Step 3 tab, header accent |
| Meesho | `#9B2335` | Step 3 tab, header accent |

---

## Known Technical Debt

| Issue | Location | Impact |
|---|---|---|
| No module system — all 2500 lines in one file | `app.js` | Hard to navigate; no code splitting |
| Global mutable state | `app.js` top-level vars | Debugging wizard bugs requires tracking all globals |
| No error boundary — any unhandled throw in render crashes the page | All render functions | Silent failures hard to trace |
| `renderDashboard` re-fetches ALL products (up to 200) on every visit | `renderDashboard()` | Performance degrades with large catalogs |
| No offline caching for API responses | All fetch calls | Network glitch during wizard loses progress |
