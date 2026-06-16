# WPACS Desktop Agent

The Windows Desktop Agent runs in the signed-in Windows session and sends approved workstation events to the WPACS API.

Events:

- `SHIFT_START`
- `SHIFT_END`
- `LOCK`
- `UNLOCK`
- `LOGIN`
- `LOGOFF`
- `HEARTBEAT`

The agent does not capture screenshots, keystrokes, mouse tracking, webcam, audio, browser history, file contents, or application content.
