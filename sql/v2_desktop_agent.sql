BEGIN;

ALTER TABLE agent_status
  DROP CONSTRAINT IF EXISTS agent_status_last_event_type_check;

ALTER TABLE agent_status
  ADD CONSTRAINT agent_status_last_event_type_check
  CHECK (
    last_event_type IS NULL
    OR last_event_type IN ('LOGIN', 'LOGOUT', 'LOGOFF', 'LOCK', 'UNLOCK', 'HEARTBEAT', 'SHIFT_START', 'SHIFT_END')
  );

ALTER TABLE workstation_events
  DROP CONSTRAINT IF EXISTS workstation_events_event_type_check;

ALTER TABLE workstation_events
  ADD CONSTRAINT workstation_events_event_type_check
  CHECK (event_type IN ('LOGIN', 'LOGOUT', 'LOGOFF', 'LOCK', 'UNLOCK', 'HEARTBEAT', 'SHIFT_START', 'SHIFT_END'));

COMMIT;
