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

CREATE INDEX IF NOT EXISTS idx_productivity_daily_date ON productivity_daily(date DESC);
