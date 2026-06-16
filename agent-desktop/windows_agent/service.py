import servicemanager
import win32event
import win32service
import win32serviceutil

from .main import WindowsAgent

WTS_SESSION_LOGON = 0x5
WTS_SESSION_LOGOFF = 0x6
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8


class WPACSAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WPACSDesktopAgent"
    _svc_display_name_ = "WPACS Desktop Agent"
    _svc_description_ = "Sends Windows lock, unlock, logon, logoff, and heartbeat events to WPACS."
    _svc_accepts_ = win32service.SERVICE_ACCEPT_STOP | win32service.SERVICE_ACCEPT_SESSIONCHANGE

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.agent = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.agent:
            self.agent.stop()
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("WPACS Desktop Agent starting")
        self.agent = WindowsAgent()
        try:
            self.agent.start_background()
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        except Exception as exc:
            servicemanager.LogErrorMsg(f"WPACS Desktop Agent failed: {exc}")
            raise

    def SvcOtherEx(self, control, event_type, data):
        if control != win32service.SERVICE_CONTROL_SESSIONCHANGE or not self.agent:
            return
        mapped = {
            WTS_SESSION_LOGON: "LOGIN",
            WTS_SESSION_LOGOFF: "LOGOFF",
            WTS_SESSION_LOCK: "LOCK",
            WTS_SESSION_UNLOCK: "UNLOCK",
        }.get(event_type)
        if mapped:
            self.agent.handle_event(mapped)


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(WPACSAgentService)
