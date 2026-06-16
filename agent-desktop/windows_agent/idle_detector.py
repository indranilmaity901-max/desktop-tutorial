import ctypes
from ctypes import wintypes


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def idle_seconds() -> int:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0
    tick_count = ctypes.windll.kernel32.GetTickCount()
    return max(0, int((tick_count - info.dwTime) / 1000))
