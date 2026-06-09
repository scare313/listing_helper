# TICKET-01 — Fix Marketplace Title Character Limit Display

**Sprint**: NEXT_SPRINT.md — TASK-01
**Remediates**: Audit finding R-10
**Severity**: Medium
**Estimated effort**: XS (< 30 minutes)
**Dependencies**: None
**Assigned to**: Gemini

---

## Objective

The standalone Content editor (reachable from the "Content" page in the sidebar) displays incorrect
character limits for Flipkart and Meesho title fields. Sellers are led to shorten their titles
prematurely, hurting listing quality and SEO on both marketplaces.

**Ground truth** (from `config.py` — `MARKETPLACE_LIMITS`, lines 241–262, which is the single
authoritative source for all character limits in this project):

| Marketplace | Field | Correct limit | Current display | Current counter logic |
|---|---|---|---|---|
| Amazon | Title | 200 chars | ✅ `0 / 200 chars` | ✅ `200` |
| Flipkart | Title | **500** chars | ❌ `0 / 100 chars` | ❌ `100` |
| Meesho | Title | **200** chars | ❌ `0 / 120 chars` | ❌ `120` |

Both bugs live in a single file: `static/js/app.js`.
There are exactly **two locations** to fix, both found in this audit.

---

## Files to Modify

| File | Lines | Nature of change |
|---|---|---|
| `static/js/app.js` | Line 1012 | Static HTML template string — initial display label |
| `static/js/app.js` | Line 1089 | Dynamic counter update logic — `max` variable ternary |

**No other files require changes.** `config.py`, `index.html`, `styles.css`, and all backend files are untouched.

---

## Pre-Implementation Reading

Before making any change, read the following and confirm understanding:

1. `config.py` lines 241–262 — `MARKETPLACE_LIMITS` dict. This is the authoritative source.
2. `static/js/app.js` lines 1005–1111 — the complete Flipkart and Meesho editor rendering block
   plus the `runLiveKeywordChecker()` function that updates counters in real time.
3. Understand the flow:
   - When the user switches to the Flipkart or Meesho tab in the Content editor,
     `switchMarketplaceTab(mp)` (around line 968) calls `renderContentWorkspace()`.
   - `renderContentWorkspace()` builds the editor HTML as a template string. For Flipkart,
     this includes the hardcoded `0 / 100 chars` label at line 1012.
   - Every keystroke in any editor field fires `runLiveKeywordChecker()`, which overwrites
     the counter text dynamically using the ternary at line 1089.
   - Both the initial label (line 1012) and the dynamic update (line 1089) must be fixed,
     or the counter will show the wrong initial value then correct itself on first keypress,
     or vice versa.

---

## Implementation Steps

### Step 1 — Fix the Static Display Label (Line 1012)

**Location**: `static/js/app.js`, line 1012

**Current text**:
```
        <div class="char-counter" id="cnt-title">0 / 100 chars</div>
```

**Target text**:
```
        <div class="char-counter" id="cnt-title">0 / 500 chars</div>
```

This is inside the Flipkart branch of `renderContentWorkspace()` — confirm the surrounding
context by checking that line 1006 starts with `} else if (mp === 'flipkart') {` and that
line 1031 ends that block with `};`.

Do **not** change the Amazon label at the equivalent position (around line 984, which shows
`0 / 200 chars` — this is correct).

### Step 2 — Fix the Meesho Static Display Label (Line 1038)

**Location**: `static/js/app.js`, line 1038

**Current text**:
```
        <div class="char-counter" id="cnt-title">0 / 120 chars</div>
```

**Target text**:
```
        <div class="char-counter" id="cnt-title">0 / 200 chars</div>
```

This is inside the Meesho `else` branch starting at line 1032 (`} else {`).
Confirm the surrounding context before editing.

### Step 3 — Fix the Dynamic Counter Max Variable (Line 1089)

**Location**: `static/js/app.js`, line 1089

**Current text**:
```javascript
    const max = currentActiveMarketplaceTab === 'amazon' ? 200 : (currentActiveMarketplaceTab === 'flipkart' ? 100 : 120);
```

**Target text**:
```javascript
    const max = currentActiveMarketplaceTab === 'amazon' ? 200 : (currentActiveMarketplaceTab === 'flipkart' ? 500 : 200);
```

Changes in this line:
- Flipkart: `100` → `500`
- Meesho (the final fallback): `120` → `200`

This line is inside `runLiveKeywordChecker()` (starts at line 1053). It computes the `max`
value used for the title counter's text and CSS class. The ternary evaluates
`currentActiveMarketplaceTab` which is a module-level variable tracking which of the three
marketplace tabs (amazon / flipkart / meesho) is currently visible.

### Step 4 — Verify No Other Hardcoded Instances Exist

After making the changes above, search the entire file for any remaining occurrences of the wrong values
in a title-counter context:

- Search for `100` — confirm no remaining occurrences tied to `flipkart` + `title` + `chars`
- Search for `120` — confirm no remaining occurrences tied to `meesho` + `title` + `chars`
- Search for `0 / 100` — should return zero results
- Search for `0 / 120` — should return zero results

The only `100` values that should remain after the fix are unrelated ones (e.g., `max * 0.8` threshold
arithmetic, or other constants not related to character limits).

---

## Edge Cases

### EC-01 — Counter is re-rendered on tab switch, not just initial page load
When the user switches from Amazon → Flipkart → Meesho tabs, `switchMarketplaceTab()` calls
`renderContentWorkspace()` each time, completely re-injecting the editor HTML. This means
the static label in the template string (Steps 1 and 2) is the authoritative initial value
every time a tab is selected — not just on first load. Both the static label and the dynamic
counter (line 1089) must be correct or the user will see a flash of the wrong limit on each tab switch.

### EC-02 — `runLiveKeywordChecker()` is called immediately after rendering
Line 1049 calls `runLiveKeywordChecker()` at the end of `renderContentWorkspace()`. This means
the dynamic counter overwrites the static label instantly, even with no user input. If only
one of the two locations is fixed, the counter will appear correct for a fraction of a second
then snap to the wrong value (or vice versa). Both locations must be updated in the same edit.

### EC-03 — Meesho tab does not have a `draft-keywords` counter
The Amazon tab has a third counter (`cnt-kw` at line 1003) for search terms. Flipkart and Meesho
do not. The `runLiveKeywordChecker()` function guards this with `&& currentActiveMarketplaceTab === 'amazon'`
at line 1105. This guard is not affected by this ticket — do not touch it.

### EC-04 — `0.8` warning threshold is a percentage, not an absolute value
After fixing `max`, the warning threshold formula `len > max * 0.8` re-evaluates automatically:
- Flipkart title warning fires at: `len > 500 * 0.8` = `len > 400` ✅ (correct, no code change needed)
- Meesho title warning fires at: `len > 200 * 0.8` = `len > 160` ✅ (correct, no code change needed)
The threshold logic itself does not need to change — only the `max` values.

### EC-05 — Flipkart `cnt-desc` counter (line 1025) is already correct
The Flipkart description counter at line 1025 reads `0 / 5000 chars` — this is correct per
`MARKETPLACE_LIMITS["flipkart"]["description_max_chars"] = 5000`. Do not touch it.

### EC-06 — `cnt-title` ID is reused across all three marketplace editors
All three marketplace editors use `id="cnt-title"` for the title counter. This is by design —
each tab's editor HTML completely replaces the previous one's DOM, so there is never more than
one `cnt-title` in the DOM at a time. This is not a bug, but be aware that a global `querySelector('#cnt-title')` always refers to the currently visible marketplace's counter.

### EC-07 — No server restart required
These are pure frontend JavaScript changes inside a string template literal. The server
does not need to be restarted. The browser must hard-refresh (`Ctrl+Shift+R`) to bypass
any cached version of `app.js` if the server uses file caching headers.

---

## Acceptance Criteria

All of the following must be true simultaneously before this ticket is considered complete:

- [ ] **AC-01**: Navigate to Content page → select any product → click Flipkart tab.
  The title counter reads `0 / 500 chars` before any text is typed.

- [ ] **AC-02**: Type exactly 1 character in the Flipkart title field.
  The counter reads `1 / 500 chars`. CSS class is neutral (no `.warning` or `.danger`).

- [ ] **AC-03**: Type exactly 400 characters in the Flipkart title field.
  The counter reads `400 / 500 chars`. The counter div has the CSS class `warning` (yellow).

- [ ] **AC-04**: Type exactly 501 characters in the Flipkart title field.
  The counter reads `501 / 500 chars`. The counter div has the CSS class `danger` (red).

- [ ] **AC-05**: Navigate to Content page → select any product → click Meesho tab.
  The title counter reads `0 / 200 chars` before any text is typed.

- [ ] **AC-06**: Type exactly 160 characters in the Meesho title field.
  The counter reads `160 / 200 chars`. CSS class is neutral.

- [ ] **AC-07**: Type exactly 161 characters in the Meesho title field.
  The counter reads `161 / 200 chars`. The counter div has the CSS class `warning` (yellow).

- [ ] **AC-08**: Type exactly 201 characters in the Meesho title field.
  The counter reads `201 / 200 chars`. The counter div has the CSS class `danger` (red).

- [ ] **AC-09**: Navigate to Content page → select any product → click Amazon tab.
  The title counter still reads `0 / 200 chars` — **unchanged** by this fix.

- [ ] **AC-10**: Switching between tabs multiple times (Amazon → Flipkart → Meesho → Amazon)
  each time shows the correct counter for that marketplace from the moment the tab renders,
  before any input is typed.

- [ ] **AC-11**: No JavaScript errors appear in the browser console during any of the above steps.

- [ ] **AC-12**: No occurrence of `0 / 100` or `0 / 120` remains anywhere in `app.js` (grep check).

---

## Tests Required

### T-01 — Static Label Verification (Manual)

**Steps**:
1. Start the server: `python main.py`
2. Open `http://localhost:8000` in a browser
3. Navigate to the Content page (sidebar icon ✍️)
4. Select any product that has content (or create one)
5. Click the Flipkart tab in the marketplace tab strip
6. Look at the title field — the counter below it must read `0 / 500 chars`
7. Do **not** type anything yet

**Expected**: Counter shows `0 / 500 chars`
**Failure mode**: Counter shows `0 / 100 chars` → Step 1 was not applied

---

### T-02 — Dynamic Counter Verification (Manual)

**Steps**:
1. Continuing from T-01 (on Flipkart tab)
2. Click the Flipkart title input field and type any character
3. Observe the counter text

**Expected**: Counter updates to `1 / 500 chars`
**Failure mode**: Counter shows `1 / 100 chars` → Step 3 was not applied

---

### T-03 — Warning Threshold Verification (Manual)

**Steps**:
1. On Flipkart tab with an empty title field
2. Paste or type exactly 401 characters into the Flipkart title
3. Inspect the counter div's CSS class using DevTools

**Expected**: Counter div has class `char-counter warning` and text `401 / 500 chars`
**Failure mode A**: Text shows `401 / 100 chars` → Step 3 not applied
**Failure mode B**: No `warning` class applied → threshold arithmetic broken (should not happen
if only `max` was changed, but verify)

---

### T-04 — Danger Threshold Verification (Manual)

**Steps**:
1. On Flipkart tab, type 501 characters into the Flipkart title

**Expected**: Counter div has class `char-counter danger` and text `501 / 500 chars`

---

### T-05 — Meesho Limit Verification (Manual)

**Steps**:
1. Switch to the Meesho tab
2. Verify the title counter shows `0 / 200 chars`
3. Type 165 characters → verify `warning` class
4. Type 201 characters → verify `danger` class

**Expected**: All three checks pass
**Failure mode**: Shows `0 / 120 chars` → Step 2 and/or Step 3 not applied

---

### T-06 — Amazon Regression Check (Manual)

**Steps**:
1. Switch to the Amazon tab
2. Verify the title counter shows `0 / 200 chars`
3. Type 161 characters → verify `warning` class
4. Type 201 characters → verify `danger` class

**Expected**: Amazon limits unchanged from before this ticket
**Failure mode**: Any deviation → Step 3 accidentally broke the Amazon ternary

---

### T-07 — Tab-Switch Regression (Manual)

**Steps**:
1. Switch Amazon → Flipkart → Meesho → Amazon in sequence
2. On each switch, before typing anything, verify the title counter is correct for that marketplace

**Expected**:
- Amazon: `0 / 200 chars`
- Flipkart: `0 / 500 chars`
- Meesho: `0 / 200 chars`

**Failure mode**: Any tab shows wrong limit on initial render → static label (Steps 1 or 2) is wrong

---

### T-08 — Grep Regression (Automated)

Run this command from the project root to confirm no wrong values remain:

```powershell
Select-String -Path "static\js\app.js" -Pattern "0 / 100|0 / 120|flipkart.*\? 100|flipkart.*\? 120"
```

**Expected**: Zero matches returned
**Failure mode**: Any match returned → the fix was incomplete

---

## Definition of Done

- All 8 tests pass
- All 12 acceptance criteria are checked off
- The diff of `static/js/app.js` shows exactly **3 line changes** and nothing else:
  - Line 1012: `100` → `500`
  - Line 1038: `120` → `200`
  - Line 1089: two values changed (`100` → `500`, `120` → `200`)
- No other file is modified
- No server restart was required during testing
