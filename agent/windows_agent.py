import argparse
import ctypes
from datetime import datetime, timezone
import http.cookiejar
import json
import os
import signal
import sys
import threading
import urllib.error
import urllib.request

try:
    import win32api
    import win32con
    import win32gui
    import win32ts
except ImportError:
    win32api = None
    win32con = None
    win32gui = None
    win32ts = None


WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOGON = 0x5
WTS_SESSION_LOGOFF = 0x6
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
NOTIFY_FOR_THIS_SESSION = 0
CTRL_C_EVENT = 0
CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2
DEFAULT_SOURCE = "windows_desktop_agent"


class WpacsApiClient:
    def __init__(self, base_url, username, password, role, employee_id, source):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.role = role
        self.employee_id = employee_id
        self.source = source
        cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    def request(self, path, payload):
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            response_body = error.read().decode("utf-8")
            raise RuntimeError(f"WPACS API returned {error.code}: {response_body}") from error
        return json.loads(response_body) if response_body else {}

    def authenticate(self):
        self.request(
            "/api/v1/auth/login",
            {
                "username": self.username,
                "password_hash": self.password,
                "role": self.role,
            },
        )

    def send_event(self, event_type):
        payload = {
            "employee_id": self.employee_id,
            "event_type": event_type,
            "event_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": self.source,
        }
        self.request("/api/v2/events", payload)


class WindowsSessionAgent:
    def __init__(self, client, heartbeat_seconds):
        self.client = client
        self.heartbeat_seconds = heartbeat_seconds
        self.stop_event = threading.Event()
        self.hwnd = None

    def emit(self, event_type):
        self.client.send_event(event_type)
        print(f"{datetime.now(timezone.utc).isoformat()} sent {event_type}", flush=True)

    def start(self):
        self.client.authenticate()
        self.emit("LOGIN")
        self.emit("SHIFT_START")
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        self.register_shutdown_handlers()
        self.run_message_loop()

    def stop(self):
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        for event_type in ("SHIFT_END", "LOGOFF"):
            try:
                self.emit(event_type)
            except Exception as error:
                print(f"Failed to send {event_type}: {error}", file=sys.stderr, flush=True)
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)

    def heartbeat_loop(self):
        while not self.stop_event.wait(self.heartbeat_seconds):
            try:
                self.emit("HEARTBEAT")
            except Exception as error:
                print(f"Heartbeat failed: {error}", file=sys.stderr, flush=True)

    def wnd_proc(self, hwnd, message, wparam, lparam):
        if message == WM_WTSSESSION_CHANGE:
            event_type = {
                WTS_SESSION_LOCK: "LOCK",
                WTS_SESSION_UNLOCK: "UNLOCK",
                WTS_SESSION_LOGON: "LOGIN",
                WTS_SESSION_LOGOFF: "LOGOFF",
            }.get(wparam)
            if event_type == "LOGOFF":
                self.emit("SHIFT_END")
                self.emit("LOGOFF")
                self.stop_event.set()
            elif event_type:
                self.emit(event_type)
            return 0
        if message == win32con.WM_CLOSE:
            win32ts.WTSUnRegisterSessionNotification(hwnd)
            win32gui.DestroyWindow(hwnd)
            return 0
        if message == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, message, wparam, lparam)

    def run_message_loop(self):
        window_class = "WPACSWindowsSessionAgent"
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.wnd_proc
        wc.lpszClassName = window_class
        wc.hInstance = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(
            class_atom,
            window_class,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            wc.hInstance,
            None,
        )
        win32ts.WTSRegisterSessionNotification(self.hwnd, NOTIFY_FOR_THIS_SESSION)
        print("WPACS Windows Desktop Agent is running.", flush=True)
        win32gui.PumpMessages()

    def register_shutdown_handlers(self):
        def handle_console_event(event):
            if event in (CTRL_C_EVENT, CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT):
                self.stop()
                return True
            return False

        win32api.SetConsoleCtrlHandler(handle_console_event, True)
        signal.signal(signal.SIGTERM, lambda *_: self.stop())


def parse_args():
    parser = argparse.ArgumentParser(description="WPACS Windows Desktop Agent")
    parser.add_argument("--api-base-url", default=os.environ.get("WPACS_API_BASE_URL", "http://localhost:4190"))
    parser.add_argument("--username", default=os.environ.get("WPACS_AGENT_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("WPACS_AGENT_PASSWORD"))
    parser.add_argument("--role", default=os.environ.get("WPACS_AGENT_ROLE", "MANAGER"))
    parser.add_argument("--employee-id", default=os.environ.get("WPACS_AGENT_EMPLOYEE_ID"))
    parser.add_argument("--source", default=os.environ.get("WPACS_AGENT_SOURCE", DEFAULT_SOURCE))
    parser.add_argument("--heartbeat-seconds", type=int, default=int(os.environ.get("WPACS_HEARTBEAT_SECONDS", "30")))
    return parser.parse_args()


def validate_environment(args):
    if os.name != "nt" or not all((win32api, win32con, win32gui, win32ts)):
        raise SystemExit("WPACS Windows Desktop Agent requires Windows and pywin32.")
    missing = [
        name
        for name, value in {
            "WPACS_AGENT_USERNAME": args.username,
            "WPACS_AGENT_PASSWORD": args.password,
            "WPACS_AGENT_EMPLOYEE_ID": args.employee_id,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit(f"Missing required configuration: {', '.join(missing)}")
    if args.heartbeat_seconds < 5:
        raise SystemExit("Heartbeat interval must be at least 5 seconds.")


def main():
    args = parse_args()
    validate_environment(args)
    ctypes.windll.kernel32.SetConsoleTitleW("WPACS Windows Desktop Agent")
    client = WpacsApiClient(
        args.api_base_url,
        args.username,
        args.password,
        args.role,
        args.employee_id,
        args.source,
    )
    agent = WindowsSessionAgent(client, args.heartbeat_seconds)
    try:
        agent.start()
    finally:
        agent.stop()


if __name__ == "__main__":
    main()
