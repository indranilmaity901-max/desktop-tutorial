import threading


class Heartbeat:
    def __init__(self, sender, queue, interval_seconds):
        self.sender = sender
        self.queue = queue
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.stop_event.set()

    def _loop(self):
        while not self.stop_event.wait(self.interval_seconds):
            try:
                self.sender.send("HEARTBEAT")
                self.queue.replay(self.sender)
            except Exception:
                self.queue.add("HEARTBEAT")
