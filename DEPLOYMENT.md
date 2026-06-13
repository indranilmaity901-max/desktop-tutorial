# WPACS Dashboard Deployment

WPACS currently has two deployment modes.

## Production Website

Target public URL:

```text
https://dashboard.wpacs.com
```

To make this active, deploy the live SQL dashboard to a web host, then create a DNS `CNAME` record for:

```text
dashboard.wpacs.com
```

pointing to the hostname provided by the web host. After DNS is active, enable HTTPS/TLS for the custom domain in the hosting platform.

## Live SQL Dashboard

Use this mode for the working dashboard with login, employees, attendance, productivity reports, and Excel/PDF downloads.

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
```

Render will provide `PORT` automatically.

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

This mode builds the UI only. It does not include the Python API or SQLite database, so login, employee saves, attendance saves, and report downloads will not work unless a backend is hosted separately.

## Build

```bash
node scripts/build.js
```

## Hosting Options

### Netlify

- Connect this folder or GitHub repo to Netlify.
- Build command: `node scripts/build.js`
- Publish directory: `dist`
- Static UI only.

### Vercel

- Import the repo into Vercel.
- Build command: `node scripts/build.js`
- Output directory: `dist`
- Static UI only.

### GitHub Pages

- Push this repo to GitHub on the `main` branch.
- Enable GitHub Pages using GitHub Actions.
- The included workflow deploys `dist/`.
- Static UI only.
