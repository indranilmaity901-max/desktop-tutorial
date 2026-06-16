CREATE TABLE IF NOT EXISTS roles (
  role_id BIGSERIAL PRIMARY KEY,
  role_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS employees (
  employee_id TEXT PRIMARY KEY,
  employee_name TEXT NOT NULL,
  department TEXT NOT NULL,
  manager_id TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
  user_id BIGSERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role_id BIGINT NOT NULL REFERENCES roles(role_id),
  employee_id TEXT REFERENCES employees(employee_id),
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS attendance (
  attendance_id BIGSERIAL PRIMARY KEY,
  employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
  attendance_date DATE NOT NULL,
  status TEXT NOT NULL,
  worked_hours NUMERIC(8, 2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS productivity (
  productivity_id BIGSERIAL PRIMARY KEY,
  employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
  productive_hours NUMERIC(8, 2) NOT NULL DEFAULT 0,
  non_productive_hours NUMERIC(8, 2) NOT NULL DEFAULT 0,
  productivity_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
  report_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
  report_id BIGSERIAL PRIMARY KEY,
  report_name TEXT NOT NULL,
  report_type TEXT NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT NOT NULL,
  details TEXT
);

CREATE TABLE IF NOT EXISTS agent_status (
  employee_id TEXT PRIMARY KEY REFERENCES employees(employee_id) ON DELETE CASCADE,
  current_status TEXT NOT NULL DEFAULT 'OFFLINE',
  shift_state TEXT NOT NULL DEFAULT 'ENDED',
  last_event_type TEXT,
  last_activity_at TIMESTAMPTZ,
  last_heartbeat_at TIMESTAMPTZ,
  connection_status TEXT NOT NULL DEFAULT 'OFFLINE',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (current_status IN ('OFFLINE', 'ONLINE', 'LOCKED')),
  CHECK (shift_state IN ('NOT_STARTED', 'ACTIVE', 'ENDED')),
  CHECK (connection_status IN ('OFFLINE', 'ONLINE')),
  CHECK (last_event_type IS NULL OR last_event_type IN ('LOGIN', 'LOGOUT', 'LOGOFF', 'LOCK', 'UNLOCK', 'IDLE', 'HEARTBEAT', 'SHIFT_START', 'SHIFT_END'))
);

CREATE TABLE IF NOT EXISTS workstation_events (
  id BIGSERIAL PRIMARY KEY,
  employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN ('LOGIN', 'LOGOUT', 'LOGOFF', 'LOCK', 'UNLOCK', 'IDLE', 'HEARTBEAT', 'SHIFT_START', 'SHIFT_END')),
  event_timestamp TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS productivity_daily (
  employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
  date DATE NOT NULL,
  productive_minutes INTEGER NOT NULL DEFAULT 0 CHECK (productive_minutes >= 0),
  locked_minutes INTEGER NOT NULL DEFAULT 0 CHECK (locked_minutes >= 0),
  logged_out_minutes INTEGER NOT NULL DEFAULT 0 CHECK (logged_out_minutes >= 0),
  productivity_score NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (productivity_score >= 0 AND productivity_score <= 100),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (employee_id, date)
);

CREATE INDEX IF NOT EXISTS idx_attendance_employee_date ON attendance(employee_id, attendance_date DESC);
CREATE INDEX IF NOT EXISTS idx_productivity_employee_date ON productivity(employee_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees(manager_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_workstation_events_employee_time ON workstation_events(employee_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_workstation_events_type_time ON workstation_events(event_type, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_status_activity ON agent_status(last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_productivity_daily_date ON productivity_daily(date DESC);
