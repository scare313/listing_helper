# V2UI.md — UI Gap Analysis vs CLAUDE.md v2.0 Specification

> **Generated**: 2026-06-09  
> **Audit basis**: `CLAUDE.md` Phase 5 spec, current `static/index.html`, `static/js/app.js`, `static/css/styles.css`

---

## 1. Gap Analysis

### 1.1 Gaps That Break Functionality (Bugs)

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| B-01 | `renderKeywords()` line 506 | Calls `logger.error(...)` — `logger` is not defined in browser JS. Throws `ReferenceError` if the Keywords page is visited. | Keywords page crashes silently |
| B-02 | `renderExports()` line 1316 | Calls `GET /api/templates/exports` — endpoint does not exist. The correct endpoint is `POST /api/templates/export`. Exports page always shows an error toast on load. | Exports page broken |
| B-03 | `renderDashboard()` line 199 | `res.products \|\| []` — `api()` always returns the `ApiResponse` wrapper; product array is at `res.data`. Fallback to empty array silently swallows the data. | Dashboard "Recent Products" always empty on first load |
| B-04 | `renderContent()` line 839 | Same `res.products \|\| []` pattern as B-03. | Content page product sidebar always empty |
| B-05 | `renderKeywords()` line 504 | `history = res \|\| []` assigns the full `ApiResponse` wrapper when present; should be `res?.data \|\| []`. | Keyword history sidebar renders broken objects |
| B-06 | `renderKanbanBoard()` line 2932 | Products with `listing_status='listed'` are silently pushed into the `exported` group instead of a dedicated "Listed" column. Sellers cannot distinguish exported-but-not-published from live listings. | Kanban board misrepresents listing state |

---

### 1.2 Gaps vs v2.0 Spec (Missing Features)

| ID | Spec Requirement | Current State | Notes |
|----|-----------------|---------------|-------|
| G-01 | **Kanban: 6 columns** — New / Keywords Done / Content Ready / Priced / Exported / **Listed** | Only 5 columns; "Listed" missing | `listing_status='listed'` exists in DB but has no column |
| G-02 | **Wizard-first principle** — sidebar should not expose 7 disconnected standalone pages | Sidebar still has 7 nav items; Keywords, Content, Pricing, Exports all exist as standalone pages | Spec says "wizard-first: one guided flow beats 7 disconnected pages" |
| G-03 | **Step 3 per-variation tab strip** — `id="w-variation-tabs"` container in the Step 3 header | No such container; required by TASK-13 | The header row `<div>` has no ID |
| G-04 | **Step 4 margin slider** — spec says "Adjust margin slider → prices update live" | Uses `<input type="number">` not `<input type="range">` | Functional but not spec-compliant |
| G-05 | **Version badge** — should read `v2.0` | Currently `v1.0` in sidebar header | Cosmetic but visible to users |
| G-06 | **Add/Edit Product modal category list** — should match 6-category list used in wizard | Modal has only 2 options: `baseball_caps`, `home_kitchen` | Wizard has 6 correct options; modal is stale |
| G-07 | **Products page status filter** — should filter by `listing_status` workflow stages | Filter checks `amazon_status / flipkart_status / meesho_status`, not `listing_status`. Options are 'draft/ready/listed/error' — none match actual workflow states ('new', 'keywords_done', 'content_ready', 'priced', 'exported', 'listed') | Filter never matches anything |
| G-08 | **`renderProducts()` category filter** — should have all 6 categories | Only 2 categories in filter dropdown | Same staleness as G-06 |
| G-09 | **TASK-13 placeholder**: `#w-variation-tabs` element | Not present in Step 3 HTML | Needed before TASK-13 implementation |

---

### 1.3 Cosmetic / Quality Issues

| ID | Location | Issue |
|----|----------|-------|
| Q-01 | `index.html` throughout | Extensive inline `style=` attributes in static HTML. Dozens of layout decisions (grid, flex, padding) are hardcoded inline instead of using CSS classes. Makes responsive adjustments and theming harder. |
| Q-02 | `app.js` renderX functions | JS-generated HTML uses inline `style=` strings (e.g., `style="margin-top:28px"`) instead of utility classes. Same problem as Q-01, compounded by being embedded in JS strings. |
| Q-03 | Wizard modal | No `overflow-y: auto` on `.wizard-body`. On viewports shorter than ~700px the body content is clipped with no scroll. |
| Q-04 | Wizard step circles | No hover tooltip or `title` attribute on step circles. Users cannot tell what step 4 does without clicking. |
| Q-05 | `renderContent()` | `runLiveKeywordChecker()` is called after `switchMarketplaceTab()` but both reference `document.getElementById('draft-title')` which only exists after the tab's HTML is injected. Safe only because they're synchronous; fragile if async rendering is added. |
| Q-06 | Sidebar | `data-page` values in nav items do not match the page keys used in `navigateTo()` for all pages consistently (e.g., `exports` in nav vs `renderExports` function). Minor but could cause future routing bugs. |

---

## 2. Files to Modify

| File | Reason |
|------|--------|
| `static/index.html` | Fix version badge (G-05), add `#w-variation-tabs` placeholder to Step 3 header (G-09) |
| `static/js/app.js` | Fix B-01 through B-06, G-01, G-06, G-07, G-08; add "Listed" Kanban column; sync category lists |
| `static/css/styles.css` | Add `.kanban-column.listed` color variant; add wizard body scroll fix (Q-03) |

---

## 3. Components to Delete

| Component | Location | Reason |
|-----------|----------|--------|
| **Keywords standalone page** (`renderKeywords`, `triggerKeywordResearch`, `loadCachedResearch`, `renderKeywordResearchResults`) | `app.js` lines ~497–830 | Entirely superseded by Wizard Step 2. Has `logger` bug (B-01). ~330 lines dead in the primary workflow. The wizard's Step 2 is the correct implementation. |
| **Content standalone page** (`renderContent`, `renderContentWorkspace`, `switchMarketplaceTab`, `saveManualDraftsForProduct`, `generateAiDraftsForProduct`, `runLiveKeywordChecker`, `loadContentWorkspaceForProduct`) | `app.js` lines ~832–1188 | Superseded by Wizard Step 3. ~356 lines. Keeping it means maintaining two separate content editors that share no code. |
| **Pricing standalone page** (`renderPricing`, `calculateStandalonePricing`) | `app.js` lines ~1189–1305 | Superseded by Wizard Step 4 and the `/auto-price` endpoint. ~116 lines. |
| **Exports standalone page** (`renderExports`, `triggerBulkExport`) | `app.js` lines ~1306–1461 | Broken (B-02). Superseded by Wizard Step 5 for per-product export. Bulk export across products is a nice-to-have but uses the wrong endpoint. ~155 lines. |
| **Sidebar nav items**: Keywords, Content, Pricing, Exports | `index.html` lines 43–57 | Once the above JS renderers are removed, these nav links point to dead pages. |
| **Add/Edit Product modal** (`#product-modal` in HTML, `showAddProductModal`, `closeModal`, `saveProduct`) | `index.html` + `app.js` | The wizard handles new and edit flows. The modal duplicates functionality with a stale category list. Can be deleted once Products page links open the wizard instead. |

> **Delete order matters**: Remove the nav items and standalone page renderers first, then remove dead utility functions that are only called from those renderers. Do not remove the modal until the Products page table's edit/add actions are confirmed to open the wizard.

---

## 4. Components to Rebuild

### 4.1 Must Rebuild (Required for v2.0 Correctness)

| Component | Current State | Target State |
|-----------|--------------|--------------|
| **Kanban Board** (`renderKanbanBoard`) | 5 columns, misroutes `listing_status='listed'` | 6 columns: New / Keywords Done / Content Ready / Priced / Exported / **Listed**. Products move to Listed only when `listing_status='listed'`. |
| **Dashboard data fetch** (`renderDashboard`) | `res.products \|\| []` (B-03) | `res?.data \|\| []` — fix the ApiResponse unwrapping |
| **Products page data fetch** | `res.products \|\| []` (B-04) | `res?.data \|\| []` |
| **Products page status filter** | Checks mp-specific status, wrong option values (G-07) | Filter by `listing_status` with options: All / New / Keywords Done / Content Ready / Priced / Exported / Listed |
| **Products page category filter** | 2 categories (G-08) | All 6 categories |
| **Add/Edit Product modal category list** | 2 categories (G-06) | All 6 categories, or remove modal and route to wizard |
| **Step 3 header** | Plain `<div>` with no ID | Add `id="w-variation-tabs"` container between heading and "Generate AI Copies" button (required for TASK-13) |
| **Sidebar version badge** | `v1.0` | `v2.0` |

### 4.2 Should Rebuild (Spec-Aligned Improvements)

| Component | Current State | Target State |
|-----------|--------------|--------------|
| **Sidebar navigation** | 7 items including broken/redundant pages | 3–4 items: Dashboard, Products, Settings. Wizard entry points replace Keywords/Content/Pricing/Exports nav. |
| **Step 4 margin control** | `<input type="number">` | `<input type="range">` with a numeric display alongside it (spec: "adjust margin slider") |
| **Wizard body** | No scroll on short viewports | Add `overflow-y: auto` to `.wizard-body` in CSS |

---

## 5. Estimated Implementation Order

Priority is: fix bugs first → correct data flows → add Kanban "Listed" column → structural cleanup (nav, deletion) → spec polish (slider, scroll).

### Phase 1 — Bug Fixes (1–2 hours, high safety)
1. **B-03, B-04** — Fix `res.products || []` → `res?.data || []` in `renderDashboard` and `renderContent`. Two-line changes.
2. **B-05** — Fix `history = res || []` → `res?.data || []` in `renderKeywords`.
3. **B-06 + G-01** — Add "Listed" column to `renderKanbanBoard`. Stop routing `listing_status='listed'` to the exported group.
4. **B-01** — Replace `logger.error` with `console.error` in `renderKeywords` (or defer if deleting the page).
5. **B-02** — Fix `renderExports` broken API call (or defer if deleting the page).

### Phase 2 — Data Correctness (1 hour)
6. **G-06, G-07, G-08** — Sync the Add/Edit modal and Products page filter with the full 6-category list and correct `listing_status` workflow values.
7. **G-05** — Change version badge from `v1.0` to `v2.0`.

### Phase 3 — TASK-13 Prerequisite (15 minutes)
8. **G-03, G-09** — Add `id="w-variation-tabs"` container to Step 3 header in `index.html`. This is the last prerequisite before TASK-13 can be implemented.

### Phase 4 — Structural Cleanup (2–3 hours, higher risk)
9. Remove standalone page renderers (Keywords, Content, Pricing, Exports) and their utility functions.
10. Remove corresponding sidebar nav items.
11. Redirect Products page "Add Product" and row-edit actions explicitly to `openProductWizard()`.
12. Remove or repurpose the Add/Edit Product modal.
13. Rebuild sidebar to 3–4 items (Dashboard, Products, Settings).

### Phase 5 — Spec Polish (1 hour)
14. Replace Step 4 `<input type="number">` with `<input type="range">` + numeric label.
15. Add `overflow-y: auto` to `.wizard-body` in CSS.
16. Review any remaining inline styles that should be CSS classes.

---

## Summary

| Category | Count |
|----------|-------|
| Functional bugs | 6 |
| Missing spec features | 9 |
| Cosmetic/quality issues | 6 |
| Files to modify | 3 |
| Components to delete | 5 major sections (~957 JS lines) |
| Components to rebuild | 8 |
| Estimated total effort | 5–7 hours |

The highest-value quick wins are Phase 1 and Phase 2 (under 3 hours combined): they fix silent data bugs that affect the dashboard, correct the Kanban board, and align the Products page with real data. Phase 4 (structural cleanup) is the most impactful for long-term maintenance but carries the most risk of regressions and should be done after a working session with the app running.
