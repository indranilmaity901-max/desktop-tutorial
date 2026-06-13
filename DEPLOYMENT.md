# WPACS Render Deployment

WPACS has a live Python backend and SQLite database. Production-style deployment must run `live_server.py`; static-only hosting is only a frontend preview.

## Production Target

```text
https://dashboard.wpacs.com
```

## Live Backend App

Use this mode for login, employees, attendance, productivity reports, API routes, Excel/PDF downloads, and SQLite-backed data.

### Render Blueprint

This repository includes `render.yaml`.

```yaml
services:
  - type: web
    name: wpacs-dashboard
    runtime: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python scripts/init_sql.py && python live_server.py"
    envVars:
      - key: HOST
        value: 0.0.0.0
      - key: PUBLIC_URL
        value: https://dashboard.wpacs.com
```

### Render Manual Web Service Settings

If creating the service manually, use:

```text
Runtime: Python
Build command: pip install -r requirements.txt
Start command: python scripts/init_sql.py && python live_server.py
```

Environment variables:

```text
HOST=0.0.0.0
PUBLIC_URL=https://dashboard.wpacs.com
```

Do not set `PORT` manually. Render injects `PORT`, and `live_server.py` reads it automatically.

### Why The Start Command Initializes SQLite

The start command runs:

```bash
python scripts/init_sql.py && python live_server.py
```

This creates `data/wpacs.db`, applies `sql/schema.sql`, loads `sql/seed.sql`, and seeds employee, attendance, productivity, manager, user, role, report, readiness, trust, and workstation-agent demo data before the server starts.

Render instances have ephemeral filesystems on the free/native web service path. The current SQLite setup is appropriate for a seeded prototype/live demo. For durable production data, attach persistent storage or migrate to a managed database later.

## Local Verification

Run:

```bash
python scripts/init_sql.py
HOST=127.0.0.1 PORT=4190 PUBLIC_URL=http://127.0.0.1:4190 python live_server.py
```

Windows PowerShell:

```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "4190"
$env:PUBLIC_URL = "http://127.0.0.1:4190"
python scripts/init_sql.py
python live_server.py
```

Check:

```text
http://127.0.0.1:4190/
http://127.0.0.1:4190/src/main.js
http://127.0.0.1:4190/src/styles.css
http://127.0.0.1:4190/api/health
http://127.0.0.1:4190/api/live-dashboard
http://127.0.0.1:4190/api/v1/employees
```

Demo login:

```text
admin / admin_hash_001
```

## Custom Domain On Render

After the Render service is deployed:

1. Open the Render web service.
2. Go to Settings > Custom Domains.
3. Add:

```text
dashboard.wpacs.com
```

4. Render will provide a DNS target.
5. In the DNS provider for `wpacs.com`, create:

```text
Type: CNAME
Name: dashboard
Value: <render-provided-target>
```

6. Wait for DNS propagation.
7. Confirm Render issues HTTPS for `https://dashboard.wpacs.com`.
8. Update `PUBLIC_URL` in Render if needed:

```text
PUBLIC_URL=https://dashboard.wpacs.com
```

Use Render's DNS target for the backend app. Do not point `dashboard.wpacs.com` to GitHub Pages if you want API routes and SQLite behavior.

## Static Preview Only

The repository still contains static deployment configs for GitHub Pages, Netlify, and Vercel. These are not full production deployments because they cannot run:

- `live_server.py`
- `/api/v1/*`
- `/api/live-dashboard`
- SQLite-backed writes
- Excel/PDF report downloads

Use static hosting only for a visual preview.
