# WPACS Cloud Deployment

This deployment is for the real WPACS backend app. It is not a static Netlify/Vercel/GitHub Pages deployment.

## Required Public URLs

```text
https://dashboard.wpacs.com
https://agent.wpacs.com
```

One Render web service serves both hostnames:

- `dashboard.wpacs.com` serves the dashboard UI and dashboard APIs.
- `agent.wpacs.com` serves the agent API surface.

## Cloud PostgreSQL

Use Supabase PostgreSQL or Neon PostgreSQL.

The app reads the database connection from:

```text
DATABASE_URL
```

Production data must live in PostgreSQL. Do not rely on local SQLite files for production.

### Supabase Setup

1. Create a Supabase project.
2. Open Project Settings > Database.
3. Copy the PostgreSQL connection string.
4. Use the pooled connection string if Supabase recommends it for serverless/web-service usage.
5. Store it in Render as `DATABASE_URL`.

Typical format:

```text
postgresql://postgres:<password>@<host>:5432/postgres
```

### Neon Setup

1. Create a Neon project.
2. Create or select the production branch.
3. Copy the connection string from the Neon dashboard.
4. Store it in Render as `DATABASE_URL`.

Typical format:

```text
postgresql://<user>:<password>@<host>/<database>?sslmode=require
```

## PostgreSQL Migration / Init

The production initializer is:

```bash
python scripts/init_postgres.py
```

It applies:

```text
sql/schema_postgres.sql
sql/seed_postgres.sql
```

Then it seeds the generated manager, employee, attendance, and productivity demo data.

## Render Setup

Create a Render Web Service or Blueprint from this GitHub repo.

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

Do not set `PORT`. Render injects it, and `live_server.py` reads it automatically.

## Health Checks

Dashboard/general:

```text
https://dashboard.wpacs.com/health
https://dashboard.wpacs.com/api/v1/health
```

Agent:

```text
https://agent.wpacs.com/agent/v1/health
```

## Agent API Surface

The agent hostname is reserved for workstation-agent communication:

```text
GET  /agent/v1/health
POST /agent/v1/events
```

Example event post:

```json
{
  "agent_id": "WPACSAgent-001",
  "events": [
    {
      "type": "LOCK",
      "occurred_at": "2026-06-13T09:00:00Z"
    }
  ]
}
```

## Custom Domains

After the Render service is deployed:

1. Open the Render web service.
2. Go to Settings > Custom Domains.
3. Add:

```text
dashboard.wpacs.com
agent.wpacs.com
```

4. Render will show a target hostname.
5. In the DNS provider for `wpacs.com`, create:

```text
dashboard.wpacs.com  CNAME  <your-render-service>.onrender.com
agent.wpacs.com      CNAME  <your-render-service>.onrender.com
```

6. Wait for DNS propagation.
7. Confirm Render issues TLS certificates for both hostnames.

## Static Preview Warning

The Netlify/Vercel/GitHub Pages configs are preview-only. They cannot run:

- `live_server.py`
- PostgreSQL migrations
- `/api/v1/*`
- `/api/live-dashboard`
- `/agent/v1/*`
- report downloads
