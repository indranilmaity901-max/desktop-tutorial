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

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT NOT NULL,
  details TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees(manager_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
