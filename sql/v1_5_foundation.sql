BEGIN;

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
  CHECK (last_event_type IS NULL OR last_event_type IN ('LOGIN', 'LOGOUT', 'LOCK', 'UNLOCK', 'HEARTBEAT', 'SHIFT_START', 'SHIFT_END'))
);

CREATE TABLE IF NOT EXISTS workstation_events (
  id BIGSERIAL PRIMARY KEY,
  employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN ('LOGIN', 'LOGOUT', 'LOCK', 'UNLOCK', 'HEARTBEAT', 'SHIFT_START', 'SHIFT_END')),
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

CREATE INDEX IF NOT EXISTS idx_workstation_events_employee_time ON workstation_events(employee_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_workstation_events_type_time ON workstation_events(event_type, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_status_activity ON agent_status(last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_productivity_daily_date ON productivity_daily(date DESC);

COMMIT;
