# WPACS Windows Desktop Agent

The Windows Desktop Agent listens for real Windows session events and sends them to WPACS through the API.

## Events

- `SHIFT_START`
- `SHIFT_END`
- `LOCK`
- `UNLOCK`
- `LOGIN`
- `LOGOFF`
- `HEARTBEAT`

## Event Source

Events sent by this agent use `source=windows_desktop_agent` unless `WPACS_AGENT_SOURCE` is set.

## Configuration

Set these environment variables before running. Values must come from a real WPACS user account and employee record:

- `WPACS_API_BASE_URL`
- `WPACS_AGENT_USERNAME`
- `WPACS_AGENT_PASSWORD`
- `WPACS_AGENT_ROLE`
- `WPACS_AGENT_EMPLOYEE_ID`

Run with `python agent\windows_agent.py`.

The account must be authenticated by WPACS and authorized to send events for the configured employee.

## Exclusions

The agent does not capture screenshots, keystrokes, mouse tracking, webcam, audio, browser history, file contents, or application content.
