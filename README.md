# WPACS V2 SaaS Repo

WPACS V2 is organized as a clean Agent, Manager, Admin, and Desktop Agent system backed by PostgreSQL.

## Structure

- `backend/`: FastAPI API, RBAC, events, productivity, realtime.
- `frontend/`: isolated Agent, Manager, and Admin browser apps.
- `agent-desktop/`: Windows Desktop Agent modules.
- `database/`: PostgreSQL schema and migrations.
- `docker/`: container build files.
- `docs/`: V2 documentation.

## Run Backend

```powershell
Copy-Item .env.example .env
python -m pip install -r backend\requirements.txt
$env:DATABASE_URL="postgresql://wpacs:wpacs@localhost:5432/wpacs"
$env:JWT_SECRET="set-a-real-secret"
python backend\run.py
```

## Run With Docker

```powershell
docker compose up --build
```

## Desktop Agent

Install Windows-only dependencies:

```powershell
python -m pip install -r agent-desktop\requirements.txt
```

Set real WPACS credentials and run:

```powershell
python -m windows_agent.main
```

from the `agent-desktop` directory.

## Privacy Boundary

WPACS Desktop Agent sends only session and shift events: `SHIFT_START`, `SHIFT_END`, `LOCK`, `UNLOCK`, `LOGIN`, `LOGOFF`, and `HEARTBEAT`.

It does not capture screenshots, keystrokes, mouse tracking, webcam, audio, browser history, file contents, or application content.
