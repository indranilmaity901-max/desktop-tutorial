import threading


from .idle_detector import idle_seconds


class Heartbeat:
    def __init__(self, sender, queue, interval_seconds, idle_threshold_seconds):
        self.sender = sender
        self.queue = queue
        self.interval_seconds = interval_seconds
        self.idle_threshold_seconds = idle_threshold_seconds
        self.stop_event = threading.Event()
        self.idle_reported = False

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.stop_event.set()

    def _loop(self):
        while not self.stop_event.wait(self.interval_seconds):
            try:
                self.sender.send("HEARTBEAT")
                current_idle = idle_seconds()
                if current_idle >= self.idle_threshold_seconds and not self.idle_reported:
                    self.sender.send("IDLE")
                    self.idle_reported = True
                elif current_idle < self.idle_threshold_seconds:
                    self.idle_reported = False
                self.queue.replay(self.sender)
            except Exception:
                self.queue.add("HEARTBEAT")
