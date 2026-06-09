# UI_MIGRATION_PLAN.md — Listing Helper v2.0 UX Redesign

> **Scope**: Visual and interaction design only. No backend changes.  
> **Source spec**: `CLAUDE.md` Phase 5 — "Product Workflow Wizard"  
> **Design philosophy**: Wizard-first. One guided flow beats 7 disconnected pages.

---

## Part 1 — Screen-by-Screen Comparison

---

### Screen 1: Dashboard

#### Current UI
- Four stat cards in a responsive grid: Total Products (clickable, opens wizard), Amazon Listed, Flipkart Listed, Meesho Listed
- A Kanban board with **5 columns**: New → Keywords → Content → Priced → Exported. Each column holds draggable product cards. Cards show SKU, name, category, cost, and a wizard launch icon.
- A "Recent Products" table below the Kanban showing the last 5 products with status badges and action buttons
- A "Quick Actions" row at the bottom: 4 pill buttons (View Products, Open Wizard, Export Listings, Settings)
- Animated number counters on stat card values

#### Desired v2.0 UI
Per CLAUDE.md: *"| New (5) | Keywords Done (3) | Content Ready (7) | Priced (2) | Exported (12) | Listed (71) |"*
- Four stat cards: same content, clickable total card opens wizard
- Kanban board with **6 columns**: New / Keywords Done / Content Ready / Priced / Exported / **Listed**. The "Listed" column is the terminal state and should carry a visual distinction (success-green accent) to distinguish live products from in-progress ones.
- The Kanban replaces the "Recent Products" table as the primary data view — the table is redundant when the Kanban is visible
- Quick Actions are redundant: each Kanban card already has a wizard icon. Remove the Quick Actions row and replace with a single "Add New Product" banner/CTA shown only when the board is empty

#### Components to Remove
- "Recent Products" table section (replaced by full Kanban)
- "Quick Actions" row of 4 pill buttons

#### Components to Redesign
- **Kanban board** (`renderKanbanBoard`, `.kanban-board`): Change CSS grid from `repeat(5, 1fr)` to `repeat(6, 1fr)`. Add a `.kanban-column.listed` variant with a green-tinted column header and border-left using `var(--accent-success)`. Products with `listing_status='listed'` get their own column instead of being merged into Exported.
- **Stat cards**: Change "Total Products" label from "(Click to Onboard)" to simply "Total Products". The stat card being clickable is non-obvious; add a small "＋ New" chip inside the card to make the affordance explicit.

#### Components to Create
- **Empty board CTA**: When `allProducts.length === 0`, render a centred hero panel with an "Add your first product" prompt and a primary `openProductWizard()` button. Remove the empty-state div that currently sits inside the table section.
- **Listed column** in the Kanban with `data-status="listed"`, green header accent, and drop-zone support consistent with existing columns.

---

### Screen 2: Products

#### Current UI
- Filter row: search bar + category filter (2 options) + status filter (draft/ready/listed/error options)
- Full product table: SKU, Name, Category, Cost, Amazon status, Flipkart status, Meesho status, Action buttons (edit, delete, wizard)
- Empty state with "Add Product" button that opens the old Add/Edit modal

#### Desired v2.0 UI
Per CLAUDE.md, the Products page is a secondary view — the wizard is the primary flow. The page should serve as a management list where every action routes to the wizard.
- Filter row: search + category filter (6 options) + **workflow-stage filter** (All / New / Keywords Done / Content Ready / Priced / Exported / Listed) replacing the marketplace-status filter
- Product table: same columns but action buttons are streamlined. The "edit" action opens the wizard at Step 1, not the old modal. "Delete" stays.
- Empty state opens the wizard, not the modal.

#### Components to Remove
- The standalone Add/Edit Product modal (`#product-modal` in HTML, `showAddProductModal`, `closeModal`, `saveProduct` in JS) — once the Products page routes all create/edit through the wizard
- The "Add Product" button on the top bar that opens the modal (replace with "New Product" → wizard)

#### Components to Redesign
- **Category filter dropdown**: Expand from 2 to 6 options matching the wizard: Baseball Caps, Home & Kitchen General, Kitchen Storage, Kitchen Tools, Home Decor, Cleaning Supplies
- **Status filter dropdown**: Replace marketplace-status options with workflow-stage options: All / New / Keywords Done / Content Ready / Priced / Exported / Listed. Filter against `listing_status` field.
- **Row action buttons**: Replace the "edit product" icon button with a "🧙 Open Wizard" button that calls `openProductWizard(p.id)`. Remove or demote the old modal-based edit.

#### Components to Create
- None — all changes are modifications to existing components

---

### Screen 3: Wizard — Step 1 (Product Specs)

#### Current UI
- Two-column layout: `300px` left panel (image dropzone + scan status + detected attributes grid) | flexible right panel (8-field form grid + variations section)
- Left panel: dashed dropzone with camera icon, drag-and-drop support, file picker, "Analyzing with Gemini..." status line, detected-attributes cards grid
- Right panel: 2-column form grid (SKU, Name, Brand, Category, Subcategory, Cost, Weight, HSN), then a full-width Variations section below
- Variations section: heading + helper text + `#w-variations-list` container + "＋ Add Variation" button
- Each variation row: type dropdown (120px) + value text input (flex:1) + SKU text input (flex:1) + remove button (28×28px)

#### Desired v2.0 UI
Per CLAUDE.md: *"Option A: Upload photo → auto-detect; Option B: Manual form entry; Add variations (color/size SKUs)"*
The spec frames these as two distinct options. Currently both panels are always visible simultaneously, which doesn't feel like a choice — it feels like a form with an optional panel attached.

- The "Option A / Option B" framing should be made visible. Add a small toggle or tabs at the top of the step: **"📸 Scan Image"** | **"✏️ Manual Entry"** — clicking Scan Image collapses the form grid, clicking Manual Entry collapses the dropzone. On wider screens (900px+), both can remain side by side as now.
- The variations section is correctly positioned. The helper text is good. No structural change needed.

#### Components to Remove
- None — the structural layout is correct

#### Components to Redesign
- **Step header framing**: Add an "Option A / Option B" toggle or a simple two-tab row above the two-column grid to make the dual-path intent explicit. This is a cosmetic UX signal, not a functional change.
- **Detected attributes display**: The current 2-column auto-fit grid of `detected-attr-card` items uses a fixed `max-height: 250px` with overflow. Since the left panel is already scrollable in context, this cap can be removed to show all detected fields at once.

#### Components to Create
- **Scan / Manual tab toggle** (`.step1-mode-tabs`): Two tab buttons with icons that annotate which panel is "active." On desktop, both panels are still visible; the tabs serve as visual labels only. On mobile, they would toggle visibility.

---

### Screen 4: Wizard — Step 2 (Keyword Research)

#### Current UI
- A text input for seed keyword or URL + "⚡ Start Crawler" button
- Progress section (hidden until crawl starts): step label + percent label + progress bar div + monospace status line
- Results section (hidden until crawl completes): two `keyword-group-card` panels side by side — Primary/Autocomplete pills | Secondary/Long-tail pills

#### Desired v2.0 UI
Per CLAUDE.md: *"Auto-triggered on entering this step."* Currently the user must click "Start Crawler" manually. This is the most significant UX gap in Step 2.

- When the user navigates to Step 2 (via "Next" from Step 1), if `wizardProduct.name` is available, the crawler should start automatically with the product name as the seed — no button press needed
- The seed input should remain visible and editable so the user can override the seed and re-run
- The "Start Crawler" button becomes a "↺ Re-run with New Seed" button that appears after results load
- Results display should be enhanced: beyond the current two pill panels, add a compact co-occurrence pairs section (as described in CLAUDE.md NLP output) and a keyword frequency mini-table

#### Components to Remove
- "⚡ Start Crawler" as the *primary action trigger* — replace with auto-trigger on step enter. Keep the button as a "re-run" action.

#### Components to Redesign
- **Seed input + button row**: Change from the primary trigger UI to a refinement UI. Move it below the progress/results area so it's clearly secondary.
- **Results layout**: Add a third panel below the two pill groups: a small frequency table showing top 10 unigrams by count, and a "Co-occurrence pairs" section showing the most frequent bigrams.

#### Components to Create
- **Auto-trigger logic hook** in `goToWizardStep(2)`: When arriving at Step 2 with a product name and no existing results, automatically call `startWizardKeywordResearch()` with `wizardProduct.name` pre-filled.
- **Co-occurrence mini-table** panel in the results grid (`.keyword-group-card` variant styled with the `long-tail` accent colour)

---

### Screen 5: Wizard — Step 3 (AI Content Generation)

#### Current UI
- Header row: "Marketplace AI Copy Generator" heading (left) + "✨ Generate AI Copies" button (right)
- `.editor-marketplace-columns`: 3-column CSS grid — Amazon column | Flipkart column | Meesho column
- Each column: marketplace colour-coded header, title input, bullets/features textarea, description textarea
- All 8 fields have char-counter divs below them (added in TASK-06)
- No variation tabs yet

#### Desired v2.0 UI
Per CLAUDE.md: *"Three-column preview: Amazon | Flipkart | Meesho; Click any field to edit inline; Character count indicators; Per-variation tabs"*
- Header row: heading (left) + **per-variation tab strip** `id="w-variation-tabs"` (centre) + "Generate AI Copies" button (right) — the centre tab strip is currently absent
- When a product has variations, tabs appear: "Base Product | Black | Red" etc. Clicking a tab loads that variation's content into the same 3-column editor
- Char counters are present (done in TASK-06)
- 3-column layout is correct

The 3-column layout at `max-width: 900px` with 24px modal padding results in ~270px per column — tight but workable. The `editor-marketplace-column` padding (16px each side) leaves ~238px of content width per column. This is a known constraint; adding horizontal scroll within `.editor-marketplace-columns` on narrow viewports would improve the experience.

#### Components to Remove
- None

#### Components to Redesign
- **Step 3 header row**: Make it a 3-part flex row — `flex: 0 0 auto` heading | `flex: 1` variation tabs (centred, scrollable if many) | `flex: 0 0 auto` button. Currently the heading and button are the only two items.
- **`.editor-marketplace-columns`**: Add `overflow-x: auto` and a `min-width` on each column (`min-width: 240px`) so that on small viewports the columns scroll horizontally rather than collapsing to unreadable widths.

#### Components to Create
- **Variation tab strip** (`#w-variation-tabs`, `.wizard-variation-tabs`): Horizontal scrollable flex row of pill tabs. Each tab is labelled with the variation value (e.g., "Black", "Red") or "Base Product". Active tab has accent background.
- **Tab active state styles** (`.wizard-var-tab`, `.wizard-var-tab.active`): Pill button, small font, accent-primary active background.

---

### Screen 6: Wizard — Step 4 (Pricing)

#### Current UI
- Left panel (240px, border-right): "Target Profit Margin (%)" `<input type="number">` with `oninput="calculateWizardPricing()"` + "Shipping Zone" `<select>` with `onchange` + informational footnote
- Right panel: 3-column grid of pricing cards — Amazon India | Flipkart Hub | Meesho Supplier. Each card: marketplace label, big price value, `.pricing-breakdown-card` with fee rows.

#### Desired v2.0 UI
Per CLAUDE.md: *"Adjust margin slider → prices update live"*
- The `<input type="number">` should be replaced by an `<input type="range">` with min=1, max=95, step=1. A numeric display sits alongside it showing the current value (e.g., "25%"). The range input updates the number display and triggers `calculateWizardPricing()` live as the user drags.
- All other structure is correct and matches the spec.
- The pricing cards are well-designed. The fee breakdown format is correct.

#### Components to Remove
- The `<input type="number" id="w-pricing-margin">` standalone input

#### Components to Redesign
- **Margin control**: Replace number input with a range slider (`<input type="range">`) + adjacent read-only number display showing the live value. The combined control should occupy the same vertical space as the current number input.

#### Components to Create
- **Margin value label** (`#w-pricing-margin-display`): A `<span>` or small `<output>` element next to the slider showing "25%" that updates in sync with the range input.

---

### Screen 7: Wizard — Step 5 (Export & Publish)

#### Current UI
- Heading: "Bulk Export Sheet Table Preview" + subheading
- Marketplace filter tabs: All | Amazon | Flipkart | Meesho (implemented in TASK-09)
- `.export-preview-table-container`: scrollable table (max-height 400px) populated dynamically
- "Mark as Published" section below the table: heading + helper text + 3 colour-coded checkboxes
- Footer: "Back" + "Export & Close" buttons

#### Desired v2.0 UI
Per CLAUDE.md: *"Full table preview in browser; Marketplace tabs (Amazon/Flipkart/Meesho/All); Download Excel button; Mark as Listed checkbox per marketplace; Done button → back to dashboard"*
- Current implementation matches the spec well for structure and function
- The main UX gap is the **button label**: the "Next" button (which becomes "Export & Close" on step 5) is generic. The spec calls it "Download & Finish" — this label communicates the action more clearly.
- The footer should also show a secondary "Skip Download" link-button for users who want to mark as listed without re-downloading.

#### Components to Remove
- None — all components match the spec

#### Components to Redesign
- **"Export & Close" button label**: Rename to "⬇ Download & Finish" to match spec language and make the download affordance explicit.
- **Step 5 subheading**: The current text ("Verify the structured data formats...") is technical. Replace with seller-facing language: "Review your listing data, then download the marketplace-ready Excel file."

#### Components to Create
- **"Skip Download" secondary action**: A `<button class="btn btn-ghost btn-sm">` link styled as "Mark as Done (skip download)" that calls `finishWizard()` with a flag to skip the Excel fetch and only update statuses.

---

### Screen 8: Settings

#### Current UI
- `.settings-grid` (responsive 2-column): Gemini API Key card | Scraper Settings card | General Defaults card
- Save button below the grid
- "Test Key Connection" button in the Gemini card

#### Desired v2.0 UI
Per CLAUDE.md: *"API key management, default preferences"*
- The settings page is functionally correct. Two UX improvements would significantly improve the experience:
  1. **Show/hide API key toggle**: The Gemini key field is `type="password"`. There is no "👁 Show" icon button. Users cannot verify what key is stored.
  2. **Save feedback**: The "Save Configurations" button fires all PUTs and shows a toast. There is no per-card save state or "last saved" timestamp. A subtle "✓ Saved" indicator near the button (shown for ~2s after success) would reinforce confidence.

#### Components to Remove
- None

#### Components to Redesign
- **API key input**: Add a show/hide toggle button (`type="button"`) inside the form group that toggles the input between `type="password"` and `type="text"`.

#### Components to Create
- **Save confirmation indicator** (`#settings-save-status`): A small inline text element next to the Save button that shows "✓ Saved" in `var(--accent-success)` for 2 seconds after a successful save, then fades out.

---

## Part 2 — Design System

Extracted from `CLAUDE.md` specification and current `styles.css`.

---

### Layout System

**Shell model**: Fixed sidebar (260px) + flexible main column. The main column is `display: flex; flex-direction: column` containing a fixed top bar (70px) and a scrollable content area.

**Content area padding**: 28px top/bottom, 32px left/right. Mobile: 20px/16px.

**Grid patterns in use**:
- Stat cards: `repeat(auto-fit, minmax(220px, 1fr))`
- Settings cards: `repeat(auto-fit, minmax(300px, 1fr))`
- Form grid: `repeat(auto-fit, minmax(200px, 1fr))`
- Kanban: `repeat(5, 1fr)` → **must change to `repeat(6, 1fr)`**
- Editor columns: `repeat(3, 1fr)` (fixed)
- Pricing cards: `repeat(3, 1fr)` (fixed)
- Wizard Step 1: `300px 1fr` (fixed)
- Pricing step left panel: `240px 1fr` (fixed)

**Wizard modal**: `max-width: 900px; max-height: 90vh`. Wizard body: `overflow-y: auto; min-height: 380px`. No max-height on the body itself — scroll is inherited from the modal's `max-height: 85vh`.

**Responsive breakpoints**:
- 768px: sidebar becomes a slide-in overlay; hamburger appears; grids collapse to 1 column
- 480px: stat cards 1-column; top bar button text hidden

---

### Navigation Model

**Model**: Persistent left sidebar with `data-page` nav links. Clicking a nav item calls `navigateTo(page)` which re-renders the `#content-area` div. No URL routing — the app is stateless on refresh.

**Active state**: `.nav-item.active` uses `border-left: 3px solid var(--accent-primary)` + `box-shadow: inset` glow.

**v2.0 target**: 3–4 nav items:
1. Dashboard (📊)
2. Products (🏷️)
3. Settings (⚙️)

The wizard is not a nav item — it is a modal overlay triggered from the Dashboard stat card, Kanban card wizard icons, Products table, and the top-bar "Add Product" button.

---

### Card System

Three card variants:

| Class | Usage | Background | Border |
|-------|-------|-----------|--------|
| `.card` | Generic content block | `var(--bg-card)` + blur | `var(--border-glass)` |
| `.stat-card` | Dashboard KPIs | Same + 3px top colour bar | Same |
| `.settings-card` | Settings sections | Same (no hover lift) | Same |

All cards: `border-radius: var(--radius-lg)` (16px), glassmorphism `backdrop-filter: blur(12px)`.

Hover: `translateY(-2px)` lift + `var(--shadow-md)` + `border-color: var(--border-glass-hover)`.

Stat card colour variants via `::before` pseudo-element top bar:
- `.accent-primary`: indigo gradient
- `.accent-amazon`: `var(--amazon-color)` solid
- `.accent-flipkart`: `var(--flipkart-color)` solid
- `.accent-meesho`: `var(--meesho-color)` solid

Missing variant: `.accent-success` for the new "Listed" Kanban column header.

---

### Table System

Two table contexts:

**Standard page tables** (Products, Exports): Wrapped in `.table-container` → `.table-wrapper` → `<table>`. Header row: 12px uppercase muted text, 1px glass border-bottom. Body rows: 14px secondary text, hover glass background, last row no border.

**Export preview table** (Wizard Step 5): Wrapped in `.export-preview-table-container`. Sticky `<thead>` with solid `#1a1a2e` background. Body `<td>` allows word-wrap (`white-space: normal; word-break: break-all`).

Row action buttons: 32×32px glass squares, danger variant on delete hover.

---

### Form System

**Form grid**: `repeat(auto-fit, minmax(200px, 1fr))` with 16px gap. Full-width override: `grid-column: 1 / -1`.

**Input styling**: `var(--bg-input)` background, glass border, 10px 14px padding, 14px font. Focus: `var(--accent-primary)` border + 3px glow ring.

**Char counter**: 11px right-aligned muted text below textarea. States: default (muted) / `.warning` (amber, >80% of limit) / `.danger` (red, >100% of limit).

**Form section titles**: 14px uppercase, 0.06em letter-spacing, 16px bottom margin.

**Filter selects** (outside form groups): `.filter-select` class — same glass styling, 36px right padding for the SVG chevron arrow.

**Select appearance**: Custom SVG chevron injected via `background-image`, `appearance: none`. Options use `var(--bg-secondary)` background.

---

### Modal System

**Overlay**: Fixed `inset: 0`, `rgba(0,0,0,0.6)` + `backdrop-filter: blur(8px)`. Toggle via `.active` class (opacity + visibility transition).

**Modal box**: `var(--bg-secondary)` background, `border-radius: var(--radius-xl)` (20px), `max-width: 680px`, `max-height: 85vh`, flex column. Entry animation: `translateY(20px) scale(0.97)` → `translateY(0) scale(1)`.

**Wizard modal**: Same system, `max-width: 900px` override, `max-height: 90vh`.

**Structure**: `.modal-header` (title + close button) / `.modal-body` (scrollable flex:1) / `.modal-footer` (right-aligned buttons, border-top).

**Close button**: 36×36px glass square, danger hover (red background).

**Variants**: `.modal-sm` (440px max-width) for destructive confirmation dialogs.

---

### Color System

**Background scale**:
- `--bg-primary: #0a0e27` — page background
- `--bg-secondary: #131842` — modal background
- `--bg-card: rgba(19,24,66,0.6)` — card surfaces
- `--bg-glass: rgba(255,255,255,0.05)` — hover states
- `--bg-input: rgba(255,255,255,0.06)` — form inputs

**Text scale**:
- `--text-primary: #f1f5f9` — headings, values
- `--text-secondary: #94a3b8` — body, labels
- `--text-muted: #64748b` — hints, counters, placeholders

**Accent scale**:
- Primary: `#6366f1` (indigo) — buttons, active nav, focus rings
- Secondary: `#06b6d4` (cyan) — SKU labels, info accents
- Success: `#10b981` (green) — listed status, completed steps, "Listed" Kanban column
- Warning: `#f59e0b` (amber) — char-counter warning state
- Danger: `#ef4444` (red) — delete, error, char-counter danger state

**Marketplace brand colors**:
- `--amazon-color: #ff9900`
- `--flipkart-color: #2874f0`
- `--meesho-color: #e8458b`

**Borders**: `--border-glass: rgba(255,255,255,0.1)` / `--border-glass-hover: rgba(255,255,255,0.2)`

**App background**: Radial gradient overlay on `var(--bg-primary)` — three ellipses in indigo/cyan/indigo at 8%/6%/4% opacity for depth.

---

### Typography

**Font**: Inter (Google Fonts), weights 400/500/600/700. System fallback stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.

**Base**: 16px, `line-height: 1.6`, antialiased.

**Scale in use**:
| Role | Size | Weight |
|------|------|--------|
| Page title | 20px | 700 |
| Modal heading | 18px | 700 |
| Card heading | 16px | 600 |
| Section title | 14px uppercase | 600 |
| Body / table | 14px | 400/500 |
| Small / labels | 13px | 500 |
| Muted / badges | 12px | 500/600 |
| Tiny / counters | 11px | 500/600 |

**Logo**: Gradient text (`text-primary` → `accent-secondary`) via `-webkit-background-clip`.

**Section title style**: Uppercase, 0.06em letter-spacing, `var(--text-secondary)` colour. Used for form sections, table headers, Kanban column headers.

---

### Spacing

**Base unit**: 4px. Common multiples in use: 4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40.

**Content area padding**: `28px 32px` desktop, `20px 16px` mobile.

**Card padding**: 24px standard, 16px compact (wizard pricing cards, Kanban cards).

**Form group gap**: 6px (label → input). Form grid gap: 16px. Form section bottom-margin: 28px.

**Sidebar**: 260px wide. Nav item padding: `12px 16px`. Nav gap: 4px.

**Top bar**: 70px height. Padding: `0 32px`.

**Transitions**: fast `0.15s ease` (hover micro-interactions), base `0.3s ease` (modal open/close, nav), slow `0.5s ease` (rarely used).

**Border radii**:
- `--radius-sm: 8px` — inputs, small buttons, pills
- `--radius-md: 12px` — buttons, row actions, row badges
- `--radius-lg: 16px` — cards, dropzones, editor columns
- `--radius-xl: 20px` — modal boxes
- `--radius-full: 9999px` — status badges, kw-pills, version badge

---

## Part 3 — UI_MIGRATION_PLAN

---

### Phase 1 — App Shell & Navigation

**Goal**: Trim the 7-item sidebar to 3 items. Remove nav links to dead/superseded pages. Update version badge.

**Files Affected**:
- `static/index.html`
- `static/js/app.js` (navigateTo function, renderer map)

**Components Created**:
- None

**Components Removed**:
- Sidebar nav items: Keywords (🔍), Content (✍️), Pricing (💰), Exports (📥)
- Corresponding entries in `navigateTo` renderer map: `keywords`, `content`, `pricing`, `exports`
- `renderKeywords`, `renderKeywordResearchResults`, `triggerKeywordResearch`, `loadCachedResearch` and their helper functions (~330 lines)
- `renderContent`, `renderContentWorkspace`, `switchMarketplaceTab`, `saveManualDraftsForProduct`, `generateAiDraftsForProduct`, `runLiveKeywordChecker`, `loadContentWorkspaceForProduct` and their helpers (~356 lines)
- `renderPricing`, `calculateStandalonePricing` (~116 lines)
- `renderExports`, `triggerBulkExport` (~155 lines)
- All CSS blocks serving only those pages: `.keywords-dashboard`, `.search-card`, `.search-input-group`, `.content-dashboard`, `.content-sidebar`, `.content-workspace`, `.mp-tabs`, `.mp-tab`, `.pane-layout`, `.draft-inputs`, `.keyword-highlight-panel`, `.kw-highlight-item`, `.metrics-grid`, `.coming-soon`, `.loading-phases`, `.loading-phase`

**Acceptance Criteria**:
- [ ] Sidebar shows exactly 3 nav items: Dashboard, Products, Settings
- [ ] Version badge reads `v2.0`
- [ ] Clicking each nav item loads its page without error
- [ ] No console errors from removed pages
- [ ] `navigateTo('keywords')` gracefully no-ops or redirects to Dashboard rather than throwing
- [ ] Total `app.js` line count decreases by at least 900 lines

---

### Phase 2 — Dashboard

**Goal**: Add the "Listed" 6th Kanban column. Remove the "Recent Products" table and "Quick Actions" row. Add an empty-state hero when no products exist.

**Files Affected**:
- `static/js/app.js` (`renderDashboard`, `renderKanbanBoard`)
- `static/css/styles.css` (`.kanban-board`, new `.kanban-column.listed`)

**Components Created**:
- **`.kanban-column.listed`** CSS variant: `border-left: 3px solid var(--accent-success)`. Column header uses `var(--accent-success)` text colour. Count badge uses `rgba(16,185,129,0.15)` background.
- **Empty-board hero panel**: Centred flex column with a 64px emoji, an `<h3>`, a description `<p>`, and a `btn btn-primary btn-pulse` button that calls `openProductWizard()`. Replaces both the empty-state div inside the table section and the Quick Actions row.

**Components Removed**:
- "Recent Products" table section from `renderDashboard` (the `renderProductsTable(recentProducts, true)` block and its section title)
- "Quick Actions" section from `renderDashboard` (the entire conditional `${recentProducts.length > 0 ? ...}` Quick Actions block)
- `.quick-actions` and `.quick-action-btn` CSS classes (once removed from Dashboard, they are unused)

**Components Redesigned**:
- **`.kanban-board`** CSS grid: `repeat(5, 1fr)` → `repeat(6, 1fr)`
- **`renderKanbanBoard`** JS function: Add a 6th column definition `{ title: 'Listed', status: 'listed', color: 'accent-success' }`. Move the current `if (status === 'listed') { groups.exported.push(p) }` logic to properly route listed products to `groups.listed`.
- **Total Products stat card**: Replace `"(Click to Onboard)"` label with `"Total Products"`. Add a `<div class="stat-card-cta">＋ Add</div>` chip inside the card (absolutely positioned, bottom-right) to surface the click affordance.

**Acceptance Criteria**:
- [ ] Dashboard shows 6 Kanban columns: New, Keywords Done, Content Ready, Priced, Exported, Listed
- [ ] "Listed" column has a green accent visual treatment distinct from all other columns
- [ ] A product with `listing_status='listed'` appears in the "Listed" column, not the "Exported" column
- [ ] Dragging a card into the "Listed" column updates `listing_status` to `'listed'` via the existing drag-drop handler
- [ ] The "Recent Products" table section is no longer present below the Kanban
- [ ] The "Quick Actions" pill row is no longer present
- [ ] When `allProducts.length === 0`, a single empty-state hero is shown with a "Start Wizard" CTA
- [ ] When products exist, the empty-state hero is absent

---

### Phase 3 — Products Page

**Goal**: Align the Products page with the wizard-first model. Expand the filter dropdowns. Route all create/edit actions through the wizard.

**Files Affected**:
- `static/js/app.js` (`renderProducts`, `filterProducts`)
- `static/index.html` (remove `#product-modal` and related HTML once wizard replaces it fully)

**Components Created**:
- None

**Components Removed**:
- `#product-modal` HTML block (Add/Edit Product modal — the entire `<div class="modal-overlay" id="product-modal">` section from `index.html`)
- `showAddProductModal`, `closeModal`, `saveProduct` JS functions
- `currentProductId`, `isEditing` state variables (used only by the old modal)

**Components Redesigned**:
- **Category filter dropdown** in `renderProducts`: Replace 2-option list with all 6 categories (Baseball Caps, Home & Kitchen General, Kitchen Storage, Kitchen Tools, Home Decor, Cleaning Supplies)
- **Status filter dropdown** in `renderProducts`: Replace `draft/ready/listed/error` options with workflow-stage options: All / New / Keywords Done / Content Ready / Priced / Exported / Listed. Update `filterProducts` to filter against `p.listing_status` instead of `p.amazon_status / flipkart_status / meesho_status`.
- **Products table row action buttons**: The "edit" icon-button (`✏️`) should call `openProductWizard(p.id)` instead of `showAddProductModal(p.id)`. Label it with a wizard icon or the text "Edit".
- **Empty state CTA**: The "Add Product" button in the empty state should call `openProductWizard()` instead of `showAddProductModal()`.
- **Top bar "Add Product" button**: Already calls `openProductWizard()`. Keep as-is.

**Acceptance Criteria**:
- [ ] Category filter shows all 6 categories and correctly filters the table
- [ ] Status filter options match the `listing_status` workflow stages
- [ ] Selecting "Content Ready" in the status filter shows only products where `listing_status === 'content_ready'`
- [ ] Clicking the edit action on a product row opens the wizard (not the old modal)
- [ ] The `#product-modal` overlay is no longer present in the DOM
- [ ] The Products page empty state opens the wizard when clicked
- [ ] The top-bar "Add Product" button opens the wizard

---

### Phase 4 — Wizard

**Goal**: Implement all spec-specified wizard UX improvements. Four sub-phases.

**Files Affected**:
- `static/index.html` (Step 1 framing, Step 3 header, Step 4 slider, Step 5 button label)
- `static/js/app.js` (Step 2 auto-trigger, Step 4 slider sync, Step 5 button label, TASK-13)
- `static/css/styles.css` (variation tabs, slider, Step 1 mode tabs, column scroll)

#### Phase 4a — Step 1: Scan/Manual Tab Toggle

**Components Created**:
- **`.step1-mode-tabs`** CSS: Horizontal flex row, two tab buttons styled like `.preview-tab` (pill variant). Labels: "📸 Scan Image" and "✏️ Manual Entry".
- On desktop (≥600px wide): Both panels remain visible simultaneously; the tabs serve as labelled indicators, not toggles.
- On mobile (<600px): Each tab toggles visibility of its respective panel.

**Components Redesigned**:
- **Step 1 two-column grid**: Add a `<div class="step1-mode-tabs">` row above the grid.

#### Phase 4b — Step 2: Auto-Trigger

**Components Redesigned**:
- **`goToWizardStep(2)` branch** in JS: When entering Step 2 and `wizardProduct.name` is available and `#w-keyword-seed` is empty, auto-populate the seed with `wizardProduct.name` and call `startWizardKeywordResearch()`.
- **Seed input + "Start Crawler" button row**: Move below the results area. Re-label button as "↺ Re-run". Show this row only after first results load (hidden during initial auto-run).

**Components Created**:
- **Co-occurrence mini-section** in keyword results: A third `.keyword-group-card` (using `long-tail` green accent) below the two pill panels. Labelled "Top Keyword Pairs". Contains a compact `<table>` of the top 8 bigrams by co-occurrence frequency from the research response.

#### Phase 4c — Step 3: Variation Tabs + Column Scroll

**Components Created**:
- **`#w-variation-tabs` container** in Step 3 header: Add as the flex:1 centred element between heading and generate button. Empty when no variations; populated by TASK-13 JS.
- **`.wizard-variation-tabs`** CSS: `display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none`. Hides scrollbar but allows horizontal scroll when many variation tabs exist.
- **`.wizard-var-tab`** CSS: Small pill button, 11px font, glass border, `var(--text-secondary)` colour.
- **`.wizard-var-tab.active`** CSS: `background: var(--accent-primary-glow); border-color: var(--accent-primary); color: #fff`.

**Components Redesigned**:
- **`.editor-marketplace-columns`**: Add `overflow-x: auto` and `min-width` of 240px per `.editor-marketplace-column` so the 3-column layout scrolls horizontally on narrow viewports rather than breaking.

#### Phase 4d — Step 4: Margin Slider

**Components Removed**:
- `<input type="number" id="w-pricing-margin">` standalone number input

**Components Created**:
- **Range + label combo**: `<input type="range" id="w-pricing-margin" min="1" max="95" step="1" value="25">` + `<span id="w-pricing-margin-display" class="margin-display-label">25%</span>`. The JS handler updates both the display label and calls `calculateWizardPricing()`.
- **`.margin-display-label`** CSS: 20px bold, `var(--text-primary)` colour, inline with the slider.

**Components Redesigned**:
- **Step 4 left panel**: Replace the `<input type="number">` row with the range slider + display label combo.

#### Phase 4e — Step 5: Button Label + Skip Download

**Components Redesigned**:
- **"Export & Close" button text**: Change in `goToWizardStep` handler from `'Export & Close'` to `'⬇ Download & Finish'`.

**Components Created**:
- **"Skip Download" ghost button**: `<button class="btn btn-ghost btn-sm">` with label "Mark as done (skip download)". Placed in the modal footer to the left of the "⬇ Download & Finish" button. Calls a `finishWizardWithoutDownload()` function that only fires the status-update PUT, skips the blob fetch.

**Acceptance Criteria (all of Phase 4)**:
- [ ] Step 1 shows "📸 Scan Image / ✏️ Manual Entry" tab labels above the two-column grid
- [ ] On viewports below 600px, the tabs toggle which panel is visible
- [ ] Step 2 auto-starts the crawler when entered with a named product (seed is pre-filled)
- [ ] The "Start Crawler" button is absent until results have loaded; then "↺ Re-run" appears below results
- [ ] Step 3 header row is a 3-part flex row (heading | tabs | button); `#w-variation-tabs` container exists
- [ ] Step 3 three-column editor scrolls horizontally on narrow viewports without text clipping
- [ ] Step 4 shows a horizontal range slider for target margin with a live "25%" label beside it
- [ ] Dragging the Step 4 slider updates the label in real time and re-calculates prices
- [ ] Step 5 footer button reads "⬇ Download & Finish"
- [ ] A "Mark as done (skip download)" ghost button is present in the Step 5 footer

---

### Phase 5 — Settings

**Goal**: Add show/hide API key toggle. Add post-save confirmation indicator.

**Files Affected**:
- `static/js/app.js` (`renderSettings`, `saveDbSettings`)
- `static/css/styles.css` (minimal additions)

**Components Created**:
- **Show/hide toggle button** inside the Gemini API key form group: A `<button type="button" class="btn-show-key">` (inline icon, 👁/🙈) that toggles `#s-gemini-key` between `type="password"` and `type="text"`. Positioned as an absolute overlay on the right side of the input (like a standard password reveal pattern).
- **Save confirmation indicator** (`#settings-save-status`): A `<span>` next to the "Save Configurations" button, initially empty. After a successful save, JS sets its text to "✓ Saved" in `var(--accent-success)` and clears it after 2 seconds via `setTimeout`.
- **`.btn-show-key`** CSS: Absolute position inside relative form group, right 12px, vertically centred. 24×24px transparent button.

**Components Removed**:
- None

**Acceptance Criteria**:
- [ ] The Gemini API key field shows bullets by default
- [ ] Clicking the eye icon reveals the key as plain text; clicking again hides it
- [ ] After clicking "Save Configurations", a "✓ Saved" indicator appears beside the button
- [ ] The indicator disappears after 2 seconds
- [ ] If the save fails, the indicator shows "✗ Failed" in `var(--accent-danger)` for 3 seconds

---

### Phase 6 — Cleanup

**Goal**: Remove orphaned CSS, consolidate inline styles, verify responsive behaviour of redesigned screens.

**Files Affected**:
- `static/css/styles.css`
- `static/js/app.js` (inline style strings)
- `static/index.html` (inline style attributes)

**Components Created**:
- None

**Components Removed**:
- All CSS class blocks that served only the deleted standalone pages (see Phase 1 list above)
- `.quick-actions`, `.quick-action-btn` (removed in Phase 2)
- `.coming-soon`, `.cs-icon`, `.cs-badge` (never used in v2.0 flow)
- Duplicate `@keyframes spin` definition (appears twice in styles.css at lines ~1165 and ~1547)

**Components Redesigned**:
- **Inline `style=` attributes on wizard step content**: Replace the most egregious layout strings (e.g., the Step 4 `style="display: grid; grid-template-columns: 240px 1fr; gap: 24px;"`) with named CSS classes (`.wizard-step4-layout`, `.wizard-step4-controls`, `.wizard-step4-cards`) to make the CSS file the single source of layout truth.
- **`renderDashboard` JS template**: Remove inline `style="margin-top:28px"` strings; replace with utility class `.mt-lg` defined in CSS as `margin-top: 28px`.

**Acceptance Criteria**:
- [ ] No orphaned CSS class blocks referencing deleted page components
- [ ] No duplicate `@keyframes` definitions
- [ ] Wizard Step 4 layout controlled by CSS class, not inline style string
- [ ] Dashboard section titles use CSS class for spacing, not inline style
- [ ] All wizard steps render correctly at 480px viewport width
- [ ] Kanban board scrolls horizontally at 768px viewport width (6 columns × ~150px min ≈ 900px)

---

## Summary Table

| Phase | Primary Goal | Files Changed | Est. Effort |
|-------|-------------|---------------|-------------|
| [DONE] 1 — App Shell | Trim sidebar to 3 items, delete 4 page renderers | html, app.js, styles.css | 2 hr |
| [DONE] 2 — Dashboard | Add Listed column, remove table/quick-actions | app.js, styles.css | 1 hr |
| [DONE] 3 — Products | Sync filters with real data model, route to wizard | app.js, index.html | 1 hr |
| 4 — Wizard | Auto-trigger Step 2, variation tabs, slider, labels | index.html, app.js, styles.css | 3 hr |
| 5 — Settings | Show/hide key, save indicator | app.js, styles.css | 0.5 hr |
| 6 — Cleanup | Remove orphaned CSS, inline style cleanup | app.js, styles.css, index.html | 1 hr |
| **Total** | | | **~8.5 hr** |

**Critical path**: Phase 1 must come before Phase 6 (Phase 6 removes CSS serving pages deleted in Phase 1). Phases 2–5 are independent of each other and can be executed in any order after Phase 1.
