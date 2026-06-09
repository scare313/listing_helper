# Deployment

---

## Local Development (Windows)

This is the standard way to run Listing Helper. The app is designed as a local tool
and this mode is fully supported.

### Prerequisites

- Python 3.10 or newer
- Google Chrome (required only if Selenium fallback scraping is used)
- ChromeDriver matching your Chrome version (required only for Selenium fallback)
- A Gemini API key — obtain free at https://aistudio.google.com/

### Setup

```bat
REM Clone or download the repo
cd C:\Automation\listing_helper

REM Create a virtual environment
python -m venv .venv
.venv\Scripts\activate

REM Install dependencies
pip install -r requirements.txt

REM Create .env from the template
copy .env.example .env

REM Open .env and set your Gemini API key:
REM   GEMINI_API_KEY=AIzaSy...
notepad .env
```

### Run

```bat
REM Option 1: via main.py (reads APP_HOST and APP_PORT from .env)
python main.py

REM Option 2: uvicorn with hot-reload (recommended for development)
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

### Stop

`Ctrl+C` in the terminal. The SQLite database is not locked after the process exits.

---

## Running on a Local Network

To let other devices on the same network access the app (e.g., from a tablet):

```bat
REM In .env:
APP_HOST=0.0.0.0
APP_PORT=8000

REM Then run:
python main.py
```

Access from other devices at `http://<your-pc-ip>:8000`.

**Security note**: The app has no authentication. Only expose it on a trusted local
network. Do not expose it to the internet.

---

## Production Deployment (Linux/VPS)

> **Not the intended use case.** Listing Helper is designed for local use by a single
> seller. The following is provided for completeness.

### Prerequisites

- Linux VPS (Ubuntu 22.04 recommended)
- Python 3.10+
- nginx (optional, for reverse proxy + TLS)
- systemd (for process supervision)

### Install

```bash
cd /opt/listing_helper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set GEMINI_API_KEY, APP_HOST=127.0.0.1
```

### systemd Service

Create `/etc/systemd/system/listing-helper.service`:

```ini
[Unit]
Description=Listing Helper
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/listing_helper
Environment=PATH=/opt/listing_helper/.venv/bin
ExecStart=/opt/listing_helper/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable listing-helper
systemctl start listing-helper
systemctl status listing-helper
```

**Important**: Always use `--workers 1`. The in-process `asyncio.Queue` used for SSE
keyword research does not work correctly with multiple workers. For multi-worker deployments
the queue would need to be replaced with Redis pub/sub.

### nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Required for SSE (Server-Sent Events)
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding on;
    }
}
```

The `proxy_buffering off` directive is required for SSE to work through nginx.
Without it, keyword research progress events will not stream to the browser.

---

## Docker (Optional)

A Dockerfile is not included in the repository. The following is a reference implementation:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Chrome for Selenium fallback (optional)
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/exports data/uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

```bash
docker build -t listing-helper .
docker run -d \
  -p 8000:8000 \
  -e GEMINI_API_KEY=AIzaSy... \
  -v $(pwd)/data:/app/data \
  listing-helper
```

Mount the `data/` directory as a volume so the database and exports persist across
container restarts.

---

## Environment Variables

All environment variables are read from `.env` at startup via `python-dotenv`.
See [CONFIGURATION.md](CONFIGURATION.md) for the full reference.

Minimum required configuration:
```env
GEMINI_API_KEY=AIzaSy...
```

All other variables have defaults that work for local development.

---

## Data Persistence

| Path | Contents | Backed up? |
|---|---|---|
| `data/listing_helper.db` | SQLite database — all products, content, pricing | **Backup this** |
| `data/exports/` | Generated Excel files | Optional — regeneratable |
| `data/uploads/` | Uploaded product images | Optional — for audit only |
| `.env` | API keys and settings | **Do not commit to git** |

The database is the only irreplaceable data. The `data/exports/` directory can be
regenerated from the database at any time via the Export step.

---

## Backup Strategy

### Simple backup (Windows Task Scheduler)

```bat
REM backup_db.bat
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%
copy C:\Automation\listing_helper\data\listing_helper.db ^
     C:\Backups\listing_helper_%TIMESTAMP%.db
```

Schedule `backup_db.bat` daily via Windows Task Scheduler.

### SQLite online backup (safe with running app)

```python
import sqlite3
import shutil

# WAL mode makes this safe to run while the app is running
src = sqlite3.connect('data/listing_helper.db')
dst = sqlite3.connect('backups/listing_helper_backup.db')
src.backup(dst)
dst.close()
src.close()
```

---

## Upgrading

1. Pull new code (or replace files)
2. Activate the virtual environment
3. `pip install -r requirements.txt` — install new/updated dependencies
4. Restart the server — `init_db()` runs `_MIGRATIONS_SQL` automatically at startup,
   adding any new columns or tables safely

No manual SQL migration scripts are needed. The migration system in `database.py` handles
schema changes automatically.

---

## Health Check

```bash
curl http://localhost:8000/api/health
# {"status": "healthy", "version": "1.0.0", "database": "data/listing_helper.db", ...}
```

Monitoring tools can poll this endpoint. A non-200 response or missing `"healthy"` status
indicates the app is down or the database is inaccessible.
