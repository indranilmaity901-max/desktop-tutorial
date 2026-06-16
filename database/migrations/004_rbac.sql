INSERT INTO roles (role_name)
VALUES ('ADMIN'), ('MANAGER'), ('SUPERVISOR'), ('AGENT')
ON CONFLICT (role_name) DO NOTHING;

CREATE OR REPLACE VIEW agents AS
SELECT
  e.employee_id AS id,
  u.user_id,
  e.manager_id,
  e.employee_id AS device_id,
  e.employee_name
FROM employees e
LEFT JOIN users u ON u.employee_id = e.employee_id;

CREATE OR REPLACE VIEW agent_events AS
SELECT
  id,
  employee_id AS agent_id,
  event_type,
  event_timestamp AS timestamp,
  jsonb_build_object('source', source, 'created_at', created_at) AS metadata
FROM workstation_events;

CREATE OR REPLACE VIEW audit_logs AS
SELECT id, actor, action, target, timestamp, details
FROM audit_log;
