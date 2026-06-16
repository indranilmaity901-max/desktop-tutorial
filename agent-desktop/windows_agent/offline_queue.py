from collections import deque


class OfflineQueue:
    def __init__(self):
        self._events = deque()

    def add(self, event_type):
        self._events.append(event_type)

    def replay(self, sender):
        remaining = deque()
        while self._events:
            event_type = self._events.popleft()
            try:
                sender.send(event_type)
            except Exception:
                remaining.append(event_type)
        self._events = remaining
