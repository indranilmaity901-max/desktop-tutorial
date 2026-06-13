# WPACS Dashboard

WPACS is a cloud PostgreSQL-backed workforce productivity and activity correlation dashboard.

Production surfaces:

- `https://dashboard.wpacs.com` - main admin/dashboard web app
- `https://agent.wpacs.com` - workstation agent API surface

This repository contains one Render web service that serves both hostnames.

## Stack

- Python backend: `live_server.py`
- PostgreSQL connection: `DATABASE_URL`
- PostgreSQL init/migration: `scripts/init_postgres.py`
- PostgreSQL SQL: `sql/schema_postgres.sql`, `sql/seed_postgres.sql`
- Frontend assets: `public/` and `src/`
- Render config: `render.yaml`

Static hosts can show a visual preview, but they do not run the Python API or connect to PostgreSQL. Use Render for the live app.

## Local Cloud-DB Run

Set `DATABASE_URL` to a Supabase or Neon PostgreSQL connection string, then run:

```bash
python scripts/init_postgres.py
python live_server.py
```

Health checks:

```text
/health
/api/v1/health
/agent/v1/health
```

Demo login:

```text
admin / admin_hash_001
```

## Render Deployment

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python scripts/init_postgres.py && python live_server.py
```

Environment variables:

```text
DATABASE_URL=<supabase-or-neon-postgres-url>
HOST=0.0.0.0
PUBLIC_URL=https://dashboard.wpacs.com
```

Do not set `PORT` manually. Render provides it automatically.

## DNS

After the Render service is created, add both custom domains in Render:

```text
dashboard.wpacs.com
agent.wpacs.com
```

Then add DNS records at the `wpacs.com` DNS provider:

```text
dashboard.wpacs.com  CNAME  <your-render-service>.onrender.com
agent.wpacs.com      CNAME  <your-render-service>.onrender.com
```

Use the exact Render target shown in the Render dashboard.
