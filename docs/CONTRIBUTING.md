# Contributing

This is a private internal tool. The guidelines below apply to any developer who works
on the codebase.

---

## Architecture Principles

Before writing code, understand the rules that keep this codebase maintainable:

1. **Routers are thin**. A router function should: validate input, call a DB function or
   module function, map errors to HTTP codes, return `ApiResponse`. Business logic does not
   belong in routers. The one existing violation (`routers/pricing.py`) is tracked as R-16.

2. **Modules are independent**. Each file in `modules/` must be importable in isolation.
   Modules may import from `config.py` and `database.py`, but never from each other or from
   `routers/`.

3. **Database access is async only**. Never call `sqlite3` directly. Always use `aiosqlite`
   via the `get_db()` context manager. Always use parameterised queries — never string-format
   SQL with user input.

4. **JSON columns are serialised in database.py**. If you add a column that stores JSON,
   add it to `JSON_COLUMNS` in `database.py` so `_row_to_dict` auto-parses it. Do not
   call `json.loads` / `json.dumps` outside of `database.py` for column values.

5. **Settings have two tiers**. Process-startup settings live in `.env` → `config.py`.
   Runtime-adjustable settings live in `app_settings` DB table. If you add a new setting
   that should be changeable without restart, read it via `await get_setting(key)` with
   `settings.*` fallback. Expose it in `routers/settings.py`.

6. **The frontend uses no framework**. Keep the SPA as vanilla JS. Do not introduce a
   bundler, TypeScript compiler, or npm dependency. If the app grows beyond maintainability
   in vanilla JS, migrate the whole frontend — don't mix frameworks.

7. **ApiResponse wraps every endpoint**. Every response must be:
   ```python
   return ApiResponse(success=True, message="OK", data=payload)
   ```
   The frontend `api()` helper depends on this shape.

---

## Code Style

### Python

- Follow PEP 8.
- Use type hints on all function signatures (parameters and return types).
- Use `async def` for all router functions and database CRUD functions.
- Use `await asyncio.to_thread(...)` to call blocking sync code from async context.
- Do not use `time.sleep()` in async code — use `await asyncio.sleep()`.
- Maximum line length: 100 characters.
- Docstrings on all public functions.

```python
# Good
async def get_product(product_id: int) -> dict | None:
    """Return the product row as a dict, or None if not found."""
    async with get_db() as db:
        row = await db.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
        return _row_to_dict(row) if row else None

# Bad
def get_product(pid):
    db = sqlite3.connect(...)
    ...
```

### JavaScript

- No framework, no transpiler — write ES2020 native JS.
- Use `const` / `let` — never `var`.
- Async functions with `async/await` — avoid raw `.then()` chains.
- Always handle errors in `try/catch` around `api()` calls — show a toast on failure.
- Name event handlers `on{Subject}{Action}` (e.g., `onProductCardClick`).
- Name render functions `render{Component}` (e.g., `renderDashboard`).

```js
// Good
async function saveWizardStep1() {
  try {
    const res = await api('/products/', 'POST', formData);
    wizardProduct = res.data;
    return true;
  } catch (err) {
    showToast(err.message, 'error');
    return false;
  }
}

// Bad
function saveStep1() {
  fetch('/api/products/', { method: 'POST', body: JSON.stringify(formData) })
    .then(r => r.json())
    .then(data => { ... });
}
```

---

## Branching Strategy

```
master          — production-ready code, deployable at any time
feature/<name>  — new features (branch from master, PR back to master)
fix/<name>      — bug fixes
```

Branch names use kebab-case: `feature/variation-bulk-import`, `fix/sse-double-complete`.

---

## Commit Conventions

Format: `type: short description (under 72 chars)`

| Type | Use for |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change with no behaviour change |
| `docs` | Documentation only |
| `test` | Tests only |
| `chore` | Dependencies, build config, CI |

Examples:
```
feat: add variation bulk import from CSV
fix: prevent double SSE complete event in keyword research
docs: add TROUBLESHOOTING guide
refactor: extract pricing logic to modules/pricing_engine.py
```

---

## Pull Request Guidelines

1. **One concern per PR**. Fix one bug or add one feature. Large PRs are harder to review.

2. **PR description must include**:
   - What changed and why
   - How to test it manually
   - Any known limitations or follow-up tasks

3. **Check before opening**:
   - Does the app start? `python main.py`
   - Does the health check pass? `curl http://localhost:8000/api/health`
   - Did you update relevant docs? (CHANGELOG.md at minimum)

4. **Security**: Never include `.env`, API keys, or database files in a PR.

---

## Adding a New Endpoint

Checklist:

- [ ] Add a Pydantic model to `models.py` for request and response bodies
- [ ] Add the router function in the appropriate `routers/` file
- [ ] If business logic is non-trivial, put it in `modules/` and call it from the router
- [ ] Add the endpoint to `docs/API_REFERENCE.md`
- [ ] Test via `/docs` (FastAPI auto-docs) or `curl`

---

## Adding a New Database Column

Checklist:

- [ ] Add to `_SCHEMA_SQL` in `database.py` (for fresh installs)
- [ ] Add a migration to `_MIGRATIONS_SQL` (for existing databases):
  ```python
  "ALTER TABLE products ADD COLUMN new_column TEXT DEFAULT ''",
  ```
- [ ] If the column stores JSON, add its name to `JSON_COLUMNS` in `database.py`
- [ ] Update the relevant Pydantic models in `models.py`
- [ ] Update `docs/DATABASE.md`

---

## Known Technical Debt (Prioritised)

These are issues that should be addressed before the codebase scales:

| ID | Issue | Effort | Priority |
|---|---|---|---|
| R-16 | Pricing business logic in `routers/pricing.py` instead of `modules/pricing_engine.py` | 2h | High |
| — | All 2500 lines of frontend JS in one file | 8h | Medium |
| — | No request logging middleware | 1h | Medium |
| — | `competitor_data` column defined but never used | 30m | Low |
| — | Version string `"1.0.0"` in `main.py` should be `"2.0.0"` | 5m | Low |
| — | No explicit per-request timeout in fast-path scraper | 1h | Medium |
| — | `renderDashboard` fetches up to 200 products on every visit | 2h | Medium |
