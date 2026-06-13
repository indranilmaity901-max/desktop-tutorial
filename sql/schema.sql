DROP TABLE IF EXISTS dashboard_metrics;
DROP TABLE IF EXISTS app_users;
DROP TABLE IF EXISTS app_roles;
DROP TABLE IF EXISTS managers;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS attendance_logs;
DROP TABLE IF EXISTS productivity_logs;
DROP TABLE IF EXISTS metric_evidence;
DROP TABLE IF EXISTS productivity_trend;
DROP TABLE IF EXISTS conflicts;
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS workstation_agent_status;
DROP TABLE IF EXISTS workstation_agent_events;
DROP TABLE IF EXISTS workstation_agent_transport;
DROP TABLE IF EXISTS workstation_agent_buffer;
DROP TABLE IF EXISTS workstation_agent_safeguards;
DROP TABLE IF EXISTS workstation_agent_deployment;
DROP TABLE IF EXISTS workstation_agent_tamper;
DROP TABLE IF EXISTS enterprise_readiness_summary;
DROP TABLE IF EXISTS enterprise_readiness;
DROP TABLE IF EXISTS enterprise_readiness_items;
DROP TABLE IF EXISTS explainability_trust;
DROP TABLE IF EXISTS state_correlation;

CREATE TABLE dashboard_metrics (
  metric_key TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  trend TEXT NOT NULL,
  tone TEXT NOT NULL,
  href TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE app_users (
  user_id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  status TEXT NOT NULL,
  created_date TEXT NOT NULL
);

CREATE TABLE app_roles (
  role_id TEXT PRIMARY KEY,
  role_name TEXT NOT NULL UNIQUE
);

CREATE TABLE managers (
  manager_id TEXT PRIMARY KEY,
  manager_name TEXT NOT NULL
);

CREATE TABLE employees (
  employee_id TEXT PRIMARY KEY,
  employee_name TEXT NOT NULL,
  department TEXT NOT NULL,
  manager_id TEXT NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY (manager_id) REFERENCES managers(manager_id)
);

CREATE TABLE attendance_logs (
  attendance_id TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL,
  attendance_date TEXT NOT NULL,
  attendance_status TEXT NOT NULL,
  scheduled_minutes INTEGER NOT NULL,
  worked_minutes INTEGER NOT NULL,
  marked_by_role TEXT NOT NULL,
  marked_by_user TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

CREATE TABLE productivity_logs (
  productivity_id TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL,
  metric_date TEXT NOT NULL,
  productive_minutes INTEGER NOT NULL,
  non_productive_minutes INTEGER NOT NULL,
  productive_percentage REAL NOT NULL,
  source_system TEXT NOT NULL,
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

CREATE INDEX idx_attendance_logs_date ON attendance_logs(attendance_date);
CREATE INDEX idx_attendance_logs_employee_date ON attendance_logs(employee_id, attendance_date);
CREATE INDEX idx_productivity_logs_date ON productivity_logs(metric_date);
CREATE INDEX idx_productivity_logs_employee_date ON productivity_logs(employee_id, metric_date);

CREATE TABLE metric_evidence (
  metric_key TEXT NOT NULL,
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  display_order INTEGER NOT NULL,
  FOREIGN KEY (metric_key) REFERENCES dashboard_metrics(metric_key)
);

CREATE TABLE productivity_trend (
  label TEXT NOT NULL,
  value INTEGER NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE conflicts (
  employee TEXT NOT NULL,
  initials TEXT NOT NULL,
  conflict_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  duration TEXT NOT NULL,
  confidence INTEGER NOT NULL,
  status TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE alerts (
  title TEXT NOT NULL,
  detail TEXT NOT NULL,
  priority TEXT NOT NULL,
  icon TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE workstation_agent_status (
  service_name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  version TEXT NOT NULL,
  status TEXT NOT NULL,
  heartbeat TEXT NOT NULL,
  cpu TEXT NOT NULL,
  memory TEXT NOT NULL,
  disk TEXT NOT NULL
);

CREATE TABLE workstation_agent_events (
  event_type TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE workstation_agent_transport (
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE workstation_agent_buffer (
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE workstation_agent_safeguards (
  label TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE workstation_agent_deployment (
  label TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE workstation_agent_tamper (
  label TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE enterprise_readiness_summary (
  score INTEGER NOT NULL,
  status TEXT NOT NULL,
  decision TEXT NOT NULL,
  blockers INTEGER NOT NULL,
  next_gate TEXT NOT NULL
);

CREATE TABLE enterprise_readiness (
  readiness_key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  icon TEXT NOT NULL,
  status TEXT NOT NULL,
  tone TEXT NOT NULL,
  owner TEXT NOT NULL,
  evidence TEXT NOT NULL,
  gap TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE enterprise_readiness_items (
  readiness_key TEXT NOT NULL,
  item TEXT NOT NULL,
  display_order INTEGER NOT NULL,
  FOREIGN KEY (readiness_key) REFERENCES enterprise_readiness(readiness_key)
);

CREATE TABLE explainability_trust (
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  target TEXT NOT NULL,
  display_order INTEGER NOT NULL
);

CREATE TABLE state_correlation (
  source TEXT NOT NULL,
  state TEXT NOT NULL,
  confidence INTEGER NOT NULL,
  display_order INTEGER NOT NULL
);
