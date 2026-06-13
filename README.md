# WPACS Dashboard

WPACS is a SQL-backed workforce productivity and activity correlation dashboard.

This repository contains the live backend app:

- Python HTTP backend: `live_server.py`
- SQLite database: `data/wpacs.db`
- Database initializer: `scripts/init_sql.py`
- Frontend assets: `public/` and `src/`
- Render deployment config: `render.yaml`

Static hosts such as GitHub Pages, Netlify, and Vercel can show a frontend preview, but they do not run the Python API or SQLite database. Use Render for the production-style live app.

## Local Run

Initialize the SQLite database and start the live backend:

```bash
python scripts/init_sql.py
python live_server.py
```

Open:

```text
http://127.0.0.1:4190/
```

Optional explicit local environment:

```bash
HOST=127.0.0.1 PORT=4190 PUBLIC_URL=http://127.0.0.1:4190 python live_server.py
```

On Windows PowerShell:

```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "4190"
$env:PUBLIC_URL = "http://127.0.0.1:4190"
python scripts/init_sql.py
python live_server.py
```

Health check:

```text
http://127.0.0.1:4190/api/health
```

Demo login:

```text
admin / admin_hash_001
```

## Render Deployment

Create a Render Web Service or Blueprint from this GitHub repository.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python scripts/init_sql.py && python live_server.py
```

Environment variables:

```text
HOST=0.0.0.0
PUBLIC_URL=https://dashboard.wpacs.com
```

Do not set `PORT` manually on Render. Render provides `PORT`; `live_server.py` reads it automatically and defaults to `4190` only for local use.

## Custom Domain

After the Render service is live:

1. In Render, open the WPACS web service.
2. Add custom domain `dashboard.wpacs.com`.
3. Render will show the DNS target for the domain.
4. In the DNS provider for `wpacs.com`, create the CNAME record Render asks for.
5. Wait for DNS propagation.
6. Enable/verify HTTPS in Render.

Typical CNAME shape:

```text
Type: CNAME
Name: dashboard
Value: <render-provided-target>
```

Use the exact target Render displays, not the GitHub Pages target, for the live backend deployment.
