# Admin Guide

This guide covers operations tasks: API key management, scraper configuration,
database maintenance, backups, and monitoring.

---

## API Key Management

### Setting the Gemini API Key

**Via the UI (recommended)**:
1. Open http://localhost:8000/settings
2. Paste the key in the "Gemini API Key" field
3. Click "Test Key" to verify
4. Click "Save"

The key is stored in the `app_settings` database table.

**Via .env (alternative)**:
Edit `.env`, set `GEMINI_API_KEY=AIzaSy...`, restart the server. The `.env` value is
used as a fallback if no key is in the database.

**Important**: Never commit the `.env` file or the database to git. The `.gitignore`
excludes both.

### Rotating the API Key

1. Generate a new key at https://aistudio.google.com/
2. Update via Settings UI (takes effect immediately) or `.env` (requires restart)
3. Use "Test Key" to confirm the new key works
4. Revoke the old key in Google AI Studio

### Gemini Free Tier Limits

| Limit | Value |
|---|---|
| Requests per minute | 15 RPM |
| Tokens per day | 1,000,000 |
| Tokens per minute | 1,000,000 |

At 15 RPM, generating content for all 3 marketplaces (3 API calls) takes ~12 seconds
minimum. For products with variations, each variation requires additional calls.
If you consistently hit rate limits, consider upgrading to a paid Gemini plan.

---

## Scraper Configuration

Scraper settings can be changed via the Settings UI without restarting the server.

### Key Settings

| Setting | Default | Recommended Range | Effect |
|---|---|---|---|
| `scraper_min_delay` | `2` | `2–5` | Minimum delay (seconds) between page requests |
| `scraper_max_delay` | `4` | `4–8` | Maximum delay (seconds) between page requests |
| `headless_browser` | `True` | Keep `True` | Whether Selenium Chrome runs without a visible window |

### When to Change Delays

- **Getting blocked frequently** (research returns only template keywords): Increase both
  delays by 1–2 seconds.
- **Research is too slow**: Do not decrease below 2 seconds — Amazon will block faster
  requests.
- **Debugging scraper issues**: Set `headless_browser` to `False` to see what the browser
  is doing.

### ChromeDriver (Selenium Fallback)

ChromeDriver is only required if the fast-path scraper (requests+BeautifulSoup) fails.
The fast-path scraper handles most cases. If Selenium is unavailable, the app falls back
to local template keywords — not ideal, but the workflow continues.

To install ChromeDriver:
1. Find your Chrome version: Chrome menu → Help → About Google Chrome
2. Download matching ChromeDriver: https://chromedriver.chromium.org/downloads
3. Place `chromedriver.exe` in a directory on your system PATH

---

## Database Management

### Database Location

Default: `data/listing_helper.db`

The path is set in `.env` via `DATABASE_PATH`. Do not move the database while the
server is running.

### Viewing the Database

Use any SQLite browser tool:
- **DB Browser for SQLite** (free, Windows/Mac/Linux): https://sqlitebrowser.org/
- **VS Code SQLite extension**: Open `.db` file directly in VS Code
- **sqlite3 CLI**: `sqlite3 data/listing_helper.db`

### Checking Database Health

```bash
sqlite3 data/listing_helper.db "PRAGMA integrity_check;"
# Should output: ok

sqlite3 data/listing_helper.db "PRAGMA wal_checkpoint(FULL);"
# Checkpoints the WAL file — run this before backups

sqlite3 data/listing_helper.db ".tables"
# Lists all tables

sqlite3 data/listing_helper.db "SELECT COUNT(*) FROM products;"
```

### Backup

The database is the only irreplaceable data in this application.

**Manual backup (Windows)**:
```bat
sqlite3 data\listing_helper.db ".backup backups\listing_helper_backup.db"
```

**Scheduled backup** (Windows Task Scheduler):
```bat
@echo off
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%
sqlite3 data\listing_helper.db ".backup backups\listing_helper_%TIMESTAMP%.db"
```

Schedule this script to run daily. The `.backup` command is safe to run while the
server is running (SQLite WAL mode ensures consistency).

**Backup what to keep**:
- Keep daily backups for 7 days
- Keep weekly backups for 4 weeks
- Monthly backups indefinitely (database is small)

### Restoring from Backup

1. Stop the server
2. Copy the backup file: `copy backups\listing_helper_backup.db data\listing_helper.db`
3. Start the server

### Cleaning Up Export Files

Generated Excel files accumulate in `data/exports/`. They are not automatically deleted.

To remove exports older than 30 days (Windows PowerShell):
```powershell
Get-ChildItem data\exports\*.xlsx |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item
```

---

## Monitoring

### Health Check

The app exposes a health check endpoint:

```
GET http://localhost:8000/api/health
```

Response when healthy:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "data/listing_helper.db",
  "export_path": "data/exports"
}
```

If this returns an error or the server doesn't respond, the app needs attention.

### Checking Server Status (Windows)

```bat
REM Check if the process is running
tasklist /FI "IMAGENAME eq python.exe"

REM View recent log output (if running in a terminal)
REM Check the terminal window where you ran `python main.py`
```

### Log Output

The app logs to stdout via Python's `logging` module. Key log lines to watch:
- `INFO:     Application startup complete.` — server started successfully
- `ERROR:    ...` — an unhandled exception occurred
- `WARNING: Selenium fallback triggered` — fast-path scraping failed (not critical)
- `WARNING: Using local fallback` — both scraping strategies failed (results degraded)

To redirect logs to a file:
```bat
python main.py > logs\app.log 2>&1
```

---

## Upgrading

1. Stop the server
2. Back up the database: `sqlite3 data\listing_helper.db ".backup data\listing_helper_pre_upgrade.db"`
3. Replace/update the application files
4. Activate the virtual environment: `.venv\Scripts\activate`
5. Update dependencies: `pip install -r requirements.txt`
6. Start the server: `python main.py`
7. The server runs `init_db()` at startup, which applies any new database migrations automatically
8. Verify: `GET http://localhost:8000/api/health`

Migrations are backwards-compatible `ALTER TABLE ... ADD COLUMN` statements. They are
safe to run on existing data and are silently ignored if the column already exists.

---

## Security Checklist

- [ ] `.env` file is not committed to git
- [ ] `data/listing_helper.db` is not committed to git
- [ ] `APP_HOST` is `127.0.0.1` (not exposed to internet)
- [ ] Gemini API key is rotated if the repository was ever accidentally made public
- [ ] Regular database backups are scheduled
- [ ] `data/uploads/` is backed up periodically (optional, for audit trail)
