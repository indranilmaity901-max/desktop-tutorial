# WPACS Technical Inventory

Date: 2026-06-05

## 1. Frontend Architecture

The current WPACS frontend is a browser-based single page dashboard implemented with plain JavaScript, HTML, and CSS.

### Current frontend files

- `public/index.html`
  - Main HTML shell.
  - Loads `src/styles.css`.
  - Loads Lucide icons from CDN.
  - Loads `src/main.js` as an ES module.
  - Includes global browser error markers on `documentElement.dataset.appError`.

- `src/main.js`
  - Main frontend application logic.
  - Renders either the login screen or dashboard into `#app`.
  - Uses template strings for UI rendering.
  - Uses browser `fetch()` for API calls.
  - Uses `sessionStorage` for login session state.
  - Handles login, logout, employee search/add, attendance marking, report fetch, and report download.

- `src/mockData.js`
  - Local fallback/static dashboard data.
  - Used when SQL-backed APIs are unavailable or for panels that are not fully backed by database data.

- `src/styles.css`
  - Full visual system for the login page and dashboard.
  - Dark enterprise/cybersecurity style with blue highlights.
  - Responsive layout for desktop/tablet/mobile.

### Frontend rendering model

The app does not currently use React, TypeScript, Vite, Material UI, Redux, TanStack Query, or React Router. Those technologies appear in the target specification, but the implemented app is currently a vanilla JavaScript SPA-style dashboard.

### Frontend state

The frontend keeps runtime state in module-level variables inside `src/main.js`, including:

- `currentUser`
- `employeeSearch`
- `reportDate`
- `reportDownloadDate`
- `employeesData`
- `attendanceLogsData`
- `rolesData`
- `dailyAttendanceReport`
- `dailyProductivityReport`
- dashboard metric datasets

### Frontend navigation

Navigation is anchor-based within one page:

- `#dashboard`
- `#employees`
- `#attendance`
- `#productivity`
- `#reports`
- `#users`
- `#roles`

No dedicated route system exists yet.

## 2. Backend Architecture

The active backend is a Python HTTP server in `live_server.py`.

### Active backend

- Runtime: Python standard library.
- Server: `ThreadingHTTPServer`.
- Request handler: custom `SimpleHTTPRequestHandler`.
- Host/port: `127.0.0.1:4190`.
- Static serving:
  - Serves files from `public/`.
  - Falls back to `public/index.html`.
  - Also serves source assets from `src/`.
- API serving:
  - Handles REST-like endpoints directly in `do_GET()` and `do_POST()`.
  - Returns JSON for most APIs.
  - Returns generated binary content for report downloads.

### Secondary backend/static server

`server.js` exists as a simple Node static file server. It serves local files and falls back to `public/index.html`, but it does not implement the SQL/API features. The live API-backed dashboard uses `live_server.py`, not `server.js`.

### Build/deployment support

- `scripts/build.js` copies `public/` and `src/` into `dist/`.
- `DEPLOYMENT.md`, `vercel.json`, `netlify.toml`, and `.github/workflows/pages.yml` describe static-site deployment.
- Static deployment would not include the Python API or SQLite backend unless separately hosted.

## 3. Database Architecture

The current database is SQLite.

### Current database file

- `data/wpacs.db`

### Schema source

- `sql/schema.sql`

### Seed source

- `sql/seed.sql`

### Database initializer

- `scripts/init_sql.py`
  - Creates `data/`.
  - Executes `sql/schema.sql`.
  - Executes `sql/seed.sql`.

### Current database model

The database is a lightweight prototype schema for:

- login users
- roles
- employees
- attendance/productivity logs
- dashboard metrics
- alerts
- conflicts
- workstation agent reference data
- enterprise readiness
- explainability
- state correlation

The database is not yet a full normalized enterprise schema. Many tables are display/reference tables for dashboard panels.

## 4. Data Source

The implemented data sources are mixed:

### Primary live data source

- SQLite database: `data/wpacs.db`
- Accessed by `live_server.py` through `sqlite3`.

### Frontend fallback/static data source

- `src/mockData.js`
- Used for fallback and non-database-backed display panels.

### Seed data

- `sql/seed.sql`
- Populates default users, roles, employees, attendance logs, dashboard metrics, alerts, conflicts, and reference panels.

### External data sources

No real external integrations are currently active.

Not yet connected:

- TCN integration
- workstation agent event ingestion from a real agent
- RabbitMQ
- Redis
- PostgreSQL
- S3/object storage
- Vault
- SignalR
- OpenTelemetry/Prometheus/Grafana

## 5. Existing APIs

The active API implementation is in `live_server.py`.

### Authentication

#### `POST /api/v1/auth/login`

Purpose: Login using role, username, and password hash.

Request fields:

- `role_name`
- `username`
- `password_hash`

Behavior:

- Validates role exists in `app_roles`.
- Validates username/password hash in `app_users`.
- Rejects inactive users.
- Returns user and role data.

Limitations:

- No JWT.
- No refresh token.
- No password hashing verification beyond direct string matching.
- No server-side session.

### Users

#### `GET /api/v1/users`

Purpose: Retrieve users.

Data source:

- `app_users`

Returns:

- `user_id`
- `username`
- `status`
- `created_date`

### Roles

#### `GET /api/v1/roles`

Purpose: Retrieve roles.

Data source:

- `app_roles`

Returns:

- `role_id`
- `role_name`

### Employees

#### `GET /api/v1/employees`

Purpose: Retrieve employee records.

Data source:

- `employees`

Returns:

- `employee_id`
- `employee_name`
- `department`
- `manager_id`
- `status`

#### `POST /api/v1/employees`

Purpose: Create employee record.

Request fields:

- `employee_id`
- `employee_name`
- `department`
- `manager_id`
- `status`

Behavior:

- Validates required fields.
- Inserts into `employees`.
- Returns `409` on duplicate employee id.

### Attendance Logs

#### `GET /api/v1/attendance-logs`

Purpose: Retrieve attendance/productivity logs.

Query parameter:

- `metric_date` optional

Data source:

- `attendance_logs`

Returns:

- `productivity_id`
- `employee_id`
- `productive_minutes`
- `non_productive_minutes`
- `productive_percentage`
- `metric_date`

#### `POST /api/v1/attendance-logs`

Purpose: Manually mark attendance/productivity log for V1.

Request fields:

- `employee_id`
- `productive_minutes`
- `non_productive_minutes`
- `metric_date`
- `productivity_id` optional

Behavior:

- Validates required fields.
- Validates employee exists.
- Calculates `productive_percentage`.
- Generates `productivity_id` if missing.
- Upserts into `attendance_logs`.

### Dashboard

#### `GET /api/live-dashboard`

Purpose: Retrieve dashboard aggregate payload.

Data source:

- `dashboard_metrics`
- `metric_evidence`
- `productivity_trend`
- `conflicts`
- `alerts`
- `workstation_agent_*`
- `enterprise_readiness_*`
- `explainability_trust`
- `state_correlation`

### Reports

#### `GET /api/v1/reports/attendance-daily`

Purpose: Retrieve daily attendance summary.

Query parameter:

- `metric_date`

Returns:

- `metric_date`
- `logged_employees`
- `productive_minutes`
- `non_productive_minutes`
- `average_productive_percentage`

#### `GET /api/v1/reports/productivity-daily`

Purpose: Retrieve employee-level daily productive report.

Query parameter:

- `metric_date`

Returns:

- `metric_date`
- `items`

Each item includes:

- `productivity_id`
- `employee_id`
- `employee_name`
- `department`
- `productive_minutes`
- `non_productive_minutes`
- `productive_percentage`
- `metric_date`

#### `GET /api/v1/reports/download`

Purpose: Download reports as Excel or PDF.

Query parameters:

- `report_type`
  - `daily-productive`
  - `attendance-summary`
- `format`
  - `xlsx`
  - `pdf`
- `metric_date`

Behavior:

- Generates an `.xlsx` file using a minimal OpenXML ZIP package.
- Generates a `.pdf` file using a minimal handcrafted PDF payload.
- Sets `Content-Disposition` attachment filename.

### Health

#### `GET /api/health`

Purpose: Basic API/database health check.

Returns:

- `database: HEALTHY`
- `api: HEALTHY`

## 6. Existing Tables

Current tables in `data/wpacs.db`:

### `app_users`

Purpose: Login user records.

Columns:

- `user_id` TEXT primary key
- `username` TEXT unique
- `password_hash` TEXT
- `status` TEXT
- `created_date` TEXT

### `app_roles`

Purpose: Role list.

Columns:

- `role_id` TEXT primary key
- `role_name` TEXT unique

Seed roles:

- Admin
- Manager
- Supervisor

### `employees`

Purpose: Employee master list.

Columns:

- `employee_id` TEXT primary key
- `employee_name` TEXT
- `department` TEXT
- `manager_id` TEXT
- `status` TEXT

### `attendance_logs`

Purpose: Manual V1 attendance/productivity logs.

Columns:

- `productivity_id` TEXT primary key
- `employee_id` TEXT foreign key to `employees.employee_id`
- `productive_minutes` INTEGER
- `non_productive_minutes` INTEGER
- `productive_percentage` REAL
- `metric_date` TEXT

### `dashboard_metrics`

Purpose: KPI cards.

Columns:

- `metric_key`
- `label`
- `value`
- `trend`
- `tone`
- `href`
- `display_order`

### `metric_evidence`

Purpose: Evidence lines under KPI cards.

Columns:

- `metric_key`
- `label`
- `value`
- `display_order`

### `productivity_trend`

Purpose: Hourly productivity chart.

Columns:

- `label`
- `value`
- `display_order`

### `conflicts`

Purpose: Display conflict queue.

Columns:

- `employee`
- `initials`
- `conflict_type`
- `severity`
- `duration`
- `confidence`
- `status`
- `display_order`

### `alerts`

Purpose: Display alert list.

Columns:

- `title`
- `detail`
- `priority`
- `icon`
- `display_order`

### Workstation agent tables

Purpose: Workstation agent reference/status display.

Tables:

- `workstation_agent_status`
- `workstation_agent_events`
- `workstation_agent_transport`
- `workstation_agent_buffer`
- `workstation_agent_safeguards`
- `workstation_agent_deployment`
- `workstation_agent_tamper`

### Enterprise readiness tables

Purpose: Enterprise readiness display.

Tables:

- `enterprise_readiness_summary`
- `enterprise_readiness`
- `enterprise_readiness_items`

### Explainability/state tables

Purpose: Trust and state-correlation display.

Tables:

- `explainability_trust`
- `state_correlation`

## 7. Implemented Features

### Login

Implemented:

- Enterprise-style WPACS login page.
- Role selection before username.
- Supported roles:
  - Admin
  - Manager
  - Supervisor
- Login against SQLite-backed users.
- Active/inactive user handling.
- Session stored in `sessionStorage`.
- Logout button.

Not implemented:

- JWT.
- Refresh tokens.
- Secure cookies.
- MFA.
- Real password hashing workflow.

### Dashboard

Implemented:

- Dark enterprise/cybersecurity dashboard design.
- Sidebar navigation.
- Topbar.
- KPI cards.
- Productivity trend chart.
- Alerts summary.
- System health card.
- Frontend Responsibilities section.
- V1 Modules section.

### Employees

Implemented:

- Employee list from SQL.
- Employee search.
- Add employee form.
- `POST /api/v1/employees`.

Not implemented:

- Edit employee.
- Delete employee.
- Employee detail page.
- Pagination.
- Department/team/manager relationship tables.

### Attendance

Implemented:

- Attendance panel.
- Admin/Manager/Supervisor messaging.
- Manual V1 attendance marking.
- Productive hours and non-productive hours entered in UI.
- Backend stores minutes.
- Productive percentage calculated by backend.
- Daily attendance report fetch.
- Daily productive report fetch.
- Shrinkage note: shrinkage is detected from data report, not attendance entry.

Not implemented:

- Role-based enforcement on the server.
- Automatic productive/non-productive detection.
- Workstation/dialer event-driven attendance calculation.
- Approval/audit workflow.

### Reports

Implemented:

- Report dropdown.
- Format dropdown.
- Date picker.
- Download button.
- Daily Productive Report download.
- Attendance Summary download.
- Excel format.
- PDF format.

Limitations:

- Excel generation is minimal OpenXML.
- PDF generation is minimal single-page text PDF.
- No stored report jobs.
- No report history.
- No scheduled reports.

### Users and Roles

Implemented:

- Users displayed in administration panel.
- Roles displayed in administration panel.
- Roles loaded from SQL.

Not implemented:

- Create/update/delete users.
- Create/update/delete roles.
- Permission assignment.
- RBAC enforcement.

### Workstation Agent

Implemented:

- Workstation agent information panel.
- Agent capabilities/status are loaded from seeded SQL/reference tables.

Not implemented:

- Real workstation agent ingestion.
- Agent install package.
- Agent heartbeat API.
- Offline queue processing.
- Tamper detection service.

### Enterprise Readiness / Explainability / State Correlation

Implemented:

- Display panels and seeded readiness/trust/state data.

Not implemented:

- Real scoring engine.
- Real state correlation engine.
- Real explainability audit trail.

## 8. Incomplete Features

### Architecture gaps versus target specification

The project specification describes a much larger system using:

- React 19
- TypeScript
- Vite
- React Router
- Redux Toolkit
- TanStack Query
- Material UI
- TailwindCSS
- ASP.NET Core 9
- PostgreSQL
- Redis
- RabbitMQ
- Hangfire
- Kubernetes
- JWT/RBAC
- OpenAPI 3.1

The implemented project is currently a prototype/dashboard:

- Vanilla JavaScript frontend.
- Python standard-library backend.
- SQLite local database.
- No production authentication.
- No event processing infrastructure.
- No queue/caching/storage integrations.

### Missing API modules from original API specification

Not implemented or only partially represented:

- `/api/v1/auth/refresh`
- `/api/v1/auth/logout`
- Full user CRUD
- Full role/permission API
- Employee detail API
- Workstation event ingestion API
- TCN integration API
- Validation/run API
- Conflict details/update lifecycle API
- Productivity API beyond attendance-derived reporting
- Dashboard role-specific APIs
- Alert acknowledgement API
- Rule engine CRUD/test APIs
- Report queue/status model
- Audit logs API
- Integration management API
- System health details beyond basic health
- OpenAPI JSON/YAML generation

### Database gaps

Missing production tables/entities for:

- organizations/tenants
- user-role mappings
- permissions
- sessions/refresh tokens
- departments
- teams
- managers as formal relationships
- events
- event envelopes
- event idempotency
- state snapshots
- rules
- conflict lifecycle
- reports/jobs/files
- audit logs
- integrations
- system health history

### Security gaps

Current implementation does not include:

- JWT issuance
- refresh tokens
- RBAC middleware
- TLS enforcement
- CSRF protection
- CSP configuration
- secure cookie session storage
- password hashing/verification
- secret management
- audit logging

### Testing gaps

No implemented automated tests were found for:

- frontend behavior
- API endpoints
- database operations
- report generation
- authentication behavior
- accessibility
- E2E flows

### Deployment gaps

Static deployment files exist, but the live SQL-backed behavior depends on `live_server.py` and `data/wpacs.db`.

Deploying only `dist/` will not provide:

- SQLite-backed APIs
- login validation
- employee creation
- attendance log persistence
- report downloads

For a live hosted site, the backend must be hosted separately or migrated into a production backend.

## Current Project Summary

WPACS is currently a functional local prototype with:

- polished enterprise login/dashboard UI
- local SQLite-backed APIs
- employee management basics
- manual attendance capture
- daily attendance/productivity reporting
- Excel/PDF report downloads
- seeded operational dashboard panels

It is not yet the full enterprise architecture described in the original WPACS specifications. The next engineering step should be deciding whether to continue hardening this local Python/SQLite prototype or migrate toward the specified React + ASP.NET Core + PostgreSQL architecture.
