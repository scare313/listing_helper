# Troubleshooting

---

## Scraper Issues

### Problem: Keyword research returns no results / only template keywords

**Symptom**: Research completes but all keywords look like `"seed_word cap"`, `"buy seed_word online"` — generic template keywords rather than real data.

**Cause**: Both scraping strategies failed. The app fell back to local template keywords.

**Diagnosis**:
1. Open the browser developer console (F12 → Console).
2. Look for SSE events — a `step: "fallback"` event means both strategies failed.
3. Check server logs for the HTTP status returned by Amazon.

**Fixes**:
- If Amazon returned 503/429: increase `SCRAPER_MIN_DELAY` and `SCRAPER_MAX_DELAY` in Settings.
- If Selenium is not installed: install Chrome + ChromeDriver, or rely on the fast-path only.
- If Amazon returned a CAPTCHA page: wait 30–60 minutes and retry. Consider using a VPN.
- If the seed URL is an Amazon bestseller URL, confirm it is the correct format: `https://www.amazon.in/gp/bestsellers/...` or `https://www.amazon.in/s?k=...`.

---

### Problem: Keyword research hangs indefinitely

**Symptom**: Progress bar starts, scraping events appear, but `complete` never fires. Browser tab stays loading.

**Cause**: A product page request timed out and the scraper is waiting for it.

**Diagnosis**: Check server logs for `requests.exceptions.Timeout` or `TimeoutException` (Selenium).

**Fixes**:
- Stop and restart the research with a lower `limit` value (try 10 instead of 25).
- The fast-path scraper has a per-request timeout. If Amazon pages are consistently slow, increase `SCRAPER_MAX_DELAY` so the request is not rushed but also add a request timeout in `_scrape_fast_path_sync` (current implementation does not set one explicitly — see KNOWN_LIMITATIONS.md).

---

### Problem: Selenium says ChromeDriver not found

**Symptom**: Server log shows `selenium.common.exceptions.WebDriverException: 'chromedriver' executable not found`.

**Cause**: ChromeDriver is not installed or not on the system PATH.

**Fix**:
1. Download ChromeDriver matching your Chrome version from https://chromedriver.chromium.org/downloads
2. Place `chromedriver.exe` (Windows) in a directory on your PATH, e.g., `C:\Windows\`.
3. Alternatively, install via pip: `pip install webdriver-manager` and update `_scrape_selenium_sync` to use `webdriver_manager`.

Note: Selenium is only invoked as a fallback. If you don't need the fallback, the fast-path scraper works without ChromeDriver.

---

## Keyword Research SSE Issues

### Problem: `TypeError: Cannot read properties of undefined (reading 'primary')`

**Symptom**: Browser console shows the above error. Keyword results don't render.

**Cause** (now fixed): The `complete` SSE event was emitted without a `results` payload by internal fallback/exception paths.

**Status**: Fixed in current version. If you see this error:
1. Confirm you are running the latest version of `modules/keyword_research.py`.
2. The fix: internal fallback paths emit `step: "fallback"` instead of `step: "complete"`. Only the router emits `complete` with the results payload.
3. The frontend null-guard in `renderWizardKeywordResults()` prevents a crash even if the payload is missing.

---

### Problem: SSE stream opens but no events appear

**Symptom**: Network tab shows the `/api/keywords/research/stream` request as "pending" with no data.

**Cause**: nginx or a reverse proxy is buffering the response.

**Fix**: Add `proxy_buffering off` and `proxy_cache off` to the nginx location block. See DEPLOYMENT.md for the full nginx config.

---

## AI Content Generation Issues

### Problem: Content generation returns 400 "Gemini API key not configured"

**Diagnosis**: `GET /api/settings/` — check `gemini_api_key_configured` is `"true"`.

**Fix**:
1. If key is missing from `.env`: edit `.env`, add `GEMINI_API_KEY=AIzaSy...`, restart server.
2. If key was set via the Settings UI: `GET /api/settings/gemini_api_key` to confirm the DB value.
3. After setting the key, use "Test API Key" in the Settings page to confirm it works before generating.

---

### Problem: Content generation returns 502 "Gemini API call failed"

**Cause**: Gemini API returned an error after all 5 retry attempts.

**Diagnosis**: Check server log for the specific error:
- `ResourceExhausted` (429) — you've hit the rate limit (15 RPM on free tier).
- `ServiceUnavailable` (503) — Gemini service is down temporarily.
- `AuthenticationError` — API key is invalid or revoked.
- `InvalidArgument` — prompt was malformed.

**Fixes**:
- Rate limit: wait 1 minute and retry. Consider upgrading to a paid Gemini tier if generating many products.
- Service unavailable: retry after a few minutes.
- Auth error: regenerate the API key at https://aistudio.google.com/ and update Settings.

---

### Problem: Generated content is truncated or truncated mid-sentence

**Cause**: The product's `notes` or other fields contained characters that confused the JSON response parser.

**Diagnosis**: Check server log for `json.JSONDecodeError` in `content_generator.py`.

**Fix**: Remove special characters (quotes, backslashes) from the product's `notes` field and regenerate.

---

## Export Issues

### Problem: Excel download doesn't start

**Symptom**: Clicking "Download & Finish" shows a success toast but no file downloads.

**Diagnosis**:
1. Check the Network tab — the `POST /api/templates/export` request should return a binary response.
2. Check the server for errors: `500 Internal Server Error` from the Excel generator.

**Fixes**:
- If the product has no content generated, the Excel will contain empty cells. This is valid but check that `amazon_title` is not null.
- If `data/exports/` directory doesn't exist: it is created automatically at startup. If permissions are wrong, create it manually: `mkdir data\exports`.

---

### Problem: Excel file opens but all content columns are empty

**Cause**: Content generation was not run before export, or content was not saved correctly.

**Diagnosis**: `GET /api/products/{id}` — check `amazon_title`, `amazon_status`, `flipkart_title`, etc.

**Fix**: Go back to wizard Step 3 and run content generation. Then proceed to Step 5.

---

## Database Issues

### Problem: Server starts but immediately crashes with `sqlite3.DatabaseError`

**Cause**: The database file is corrupted, or a previous process left a `-wal` or `-shm` file in an inconsistent state.

**Diagnosis**:
```bash
sqlite3 data/listing_helper.db "PRAGMA integrity_check;"
```

**Fix**:
- If integrity check fails: restore from backup.
- If `-wal`/`-shm` files exist and the server is not running: delete them — SQLite will recover.
- In extreme cases: `sqlite3 data/listing_helper.db ".dump" > dump.sql`, then restore from dump.

---

### Problem: `OperationalError: database is locked`

**Cause**: Two processes are writing to the database simultaneously.

**Fix**: Ensure only one instance of the app is running. SQLite WAL mode supports multiple readers but only one writer at a time. For local single-user use, this should never happen.

---

## Pricing Issues

### Problem: Pricing calculation returns unreasonably high prices

**Cause**: The iterative approximation did not converge within 20 iterations, usually because `cost_price` is very close to or higher than what the marketplace fees allow.

**Diagnosis**: Check if `cost_price` is reasonable for the category and weight. Very heavy products (>1kg) have high shipping fees that may make the target margin unachievable at any reasonable price.

**Fix**: Lower the target margin via the margin slider in Step 4, or verify that `weight_grams` is correct (common mistake: entering weight in kg instead of grams).

---

## General Issues

### Problem: App runs but I can't access it from another device on the network

**Cause**: `APP_HOST` is bound to `127.0.0.1` (localhost only).

**Fix**: Set `APP_HOST=0.0.0.0` in `.env` and restart. Then access via your PC's LAN IP
(e.g., `http://192.168.1.100:8000`).

---

### Problem: After updating the code, my settings are gone

**Cause**: The `data/listing_helper.db` file was deleted or reset.

**Fix**: Database settings (`app_settings` table) are stored in `data/listing_helper.db`.
`.env` settings are always read from the `.env` file. The database file is excluded from
`.gitignore` by design — you need to back it up manually. See DEPLOYMENT.md for backup steps.

---

### Problem: Wizard is stuck on a step / "Next" button does nothing

**Diagnosis**: Open browser console (F12) and look for JavaScript errors.

**Common causes**:
- Step 1: Required fields (`name`, `sku`) not filled — a validation error should appear.
- Step 2: Keywords research still running — the "Next" button is disabled until research completes.
- Step 3: Content not generated yet — click "Generate AI Copies" first.

If the console shows an uncaught JavaScript error, note the error message and file/line number and check KNOWN_LIMITATIONS.md for known JS issues.
