import os
import signal

from .config import load_config
from .event_sender import EventSender
from .heartbeat import Heartbeat
from .lock_detector import LockDetector
from .offline_queue import OfflineQueue


CTRL_C_EVENT = 0
CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2


class WindowsAgent:
    def __init__(self):
        self.config = load_config()
        self.sender = EventSender(self.config)
        self.queue = OfflineQueue()
        self.heartbeat = Heartbeat(
            self.sender,
            self.queue,
            self.config.heartbeat_seconds,
            self.config.idle_seconds,
        )
        self.detector = LockDetector(self.handle_event)
        self.shift_started = False
        self.authenticated = False

    def send(self, event_type):
        try:
            self.sender.send(event_type)
            self.queue.replay(self.sender)
        except Exception:
            self.queue.add(event_type)

    def handle_event(self, event_type):
        if event_type == "LOGOFF" and self.shift_started:
            self.send("SHIFT_END")
            self.shift_started = False
        self.send(event_type)

    def _start_common(self):
        self.sender.authenticate()
        self.authenticated = True
        self.send("LOGIN")
        self.send("SHIFT_START")
        self.shift_started = True
        self.heartbeat.start()

    def start(self):
        self._start_common()
        self.detector.run()

    def start_background(self):
        self._start_common()

    def stop(self):
        self.heartbeat.stop()
        if self.authenticated and self.shift_started:
            self.send("SHIFT_END")
        if self.authenticated:
            self.send("LOGOFF")
        if self.detector:
            self.detector.stop()


def main():
    if os.name != "nt":
        raise SystemExit("WPACS Desktop Agent requires Windows")
    agent = WindowsAgent()
    signal.signal(signal.SIGTERM, lambda *_: agent.stop())
    try:
        agent.start()
    finally:
        agent.stop()


if __name__ == "__main__":
    main()
