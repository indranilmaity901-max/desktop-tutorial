# WPACS V2 Production Deployment

## Required Environment

- `DATABASE_URL`
- `JWT_SECRET`
- `AUTO_MIGRATE=true`
- `WPACS_ADMIN_USERNAME`
- `WPACS_ADMIN_PASSWORD`
- `WPACS_MANAGER_USERNAME`
- `WPACS_MANAGER_PASSWORD`
- `WPACS_AGENT_USERNAME`
- `WPACS_AGENT_PASSWORD`
- `WPACS_AGENT_EMPLOYEE_ID`
- `WPACS_AGENT_EMPLOYEE_NAME`

No bootstrap identity is created unless its username and password are supplied.

## Apply Migrations Manually

```powershell
$env:DATABASE_URL="postgresql://..."
python scripts\apply_v2_migrations.py
```

## Run API

```powershell
$env:PYTHONPATH="backend"
python backend\run.py
```

## Health Check

```powershell
Invoke-WebRequest https://YOUR_API/api/v2/health -UseBasicParsing
```

The API fails startup when PostgreSQL is unreachable or required tables are missing.

## Load Validation

```powershell
python scripts\load_test_v2.py `
  --api-url https://YOUR_API `
  --database-url "postgresql://..." `
  --admin-password "REAL_ADMIN_PASSWORD" `
  --manager-password "REAL_MANAGER_PASSWORD" `
  --agents 100 `
  --manager-clients 20
```

## Desktop Agent Service

From an elevated PowerShell session:

```powershell
python -m pip install -r agent-desktop\requirements.txt
agent-desktop\installer\install_service.ps1 -PythonExe (Get-Command python).Source -RepoPath (Get-Location).Path
```

The service sends only workstation session and heartbeat events. It does not collect screenshots, keystrokes, mouse paths, webcam, audio, browser history, file contents, or application content.
