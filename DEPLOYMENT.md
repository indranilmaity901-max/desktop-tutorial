# WPACS Dashboard Deployment

WPACS V1 runs as a PostgreSQL-backed production web service.

## Production Website

Target public URLs:

```text
https://dashboard.wpacs.com
https://agent.wpacs.com
```

To make these active, deploy the backend web service to a host, then create DNS `CNAME` records for:

```text
dashboard.wpacs.com  CNAME  your-render-service.onrender.com
agent.wpacs.com      CNAME  your-render-service.onrender.com
```

The app detects the hostname automatically. `dashboard.wpacs.com` renders the manager dashboard, and `agent.wpacs.com` renders the agent dashboard. After DNS is active, add both custom domains to the same Render web service and let Render provision HTTPS/TLS.

## PostgreSQL Database

Create a PostgreSQL database on Render, Supabase, Neon, or another PostgreSQL host.

Set this environment variable on the web service:

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

Optional first-admin bootstrap:

```bash
WPACS_ADMIN_USERNAME=your-admin-user
WPACS_ADMIN_PASSWORD=your-admin-password
```

The init command creates schema and roles only. It does not seed employees, attendance, productivity, or reports.

## Live Dashboard

Use this mode for the working dashboard with login, employees, attendance, productivity records, and generated report records.

### Render

1. Push this folder to GitHub.
2. In Render, create a new Blueprint or Web Service from the repo.
3. Render can use `render.yaml`.
4. Start command:

```bash
python scripts/init_sql.py && python live_server.py
```

5. Environment variable:

```bash
HOST=0.0.0.0
PUBLIC_URL=https://dashboard.wpacs.com
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
WPACS_ADMIN_USERNAME=your-admin-user
WPACS_ADMIN_PASSWORD=your-admin-password
```

Render will provide `PORT` automatically.

6. Add both custom domains to the Render web service:

```text
dashboard.wpacs.com
agent.wpacs.com
```

7. In your DNS provider, point both subdomains to the Render service hostname:

```text
dashboard.wpacs.com  CNAME  your-render-service.onrender.com
agent.wpacs.com      CNAME  your-render-service.onrender.com
```

8. Verify both custom domains in Render.

### Railway / Heroku-style hosts

The included `Procfile` runs:

```bash
python scripts/init_sql.py && python live_server.py
```

For any host that requires explicit binding:

```bash
HOST=0.0.0.0
```

## Static Website Only

Do not use static-only hosting for production. WPACS V1 requires the Python backend and PostgreSQL APIs.

## Build

```bash
node scripts/build.js
```

## Hosting Options

### Static Hosts

Netlify, Vercel static output, and GitHub Pages are not production targets for WPACS V1 because APIs, authentication, and PostgreSQL access must be served by the backend.
