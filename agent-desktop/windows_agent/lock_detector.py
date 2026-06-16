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


class LockDetector:
    def __init__(self, on_event):
        if not all((win32api, win32con, win32gui, win32ts)):
            raise RuntimeError("Windows lock detection requires pywin32")
        self.on_event = on_event
        self.hwnd = None

    def _wnd_proc(self, hwnd, message, wparam, lparam):
        if message == WM_WTSSESSION_CHANGE:
            event_type = {
                WTS_SESSION_LOCK: "LOCK",
                WTS_SESSION_UNLOCK: "UNLOCK",
                WTS_SESSION_LOGON: "LOGIN",
                WTS_SESSION_LOGOFF: "LOGOFF",
            }.get(wparam)
            if event_type:
                self.on_event(event_type)
            return 0
        if message == win32con.WM_CLOSE:
            win32ts.WTSUnRegisterSessionNotification(hwnd)
            win32gui.DestroyWindow(hwnd)
            return 0
        if message == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, message, wparam, lparam)

    def run(self):
        window_class = "WPACSWindowsSessionAgent"
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = window_class
        wc.hInstance = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(class_atom, window_class, 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
        win32ts.WTSRegisterSessionNotification(self.hwnd, NOTIFY_FOR_THIS_SESSION)
        win32gui.PumpMessages()

    def stop(self):
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
