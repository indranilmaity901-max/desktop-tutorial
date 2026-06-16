from collections import deque
from pathlib import Path
import json
import os


class OfflineQueue:
    def __init__(self):
        queue_path = os.environ.get("WPACS_AGENT_QUEUE_PATH", "")
        self.path = Path(queue_path) if queue_path else Path.home() / ".wpacs" / "agent_queue.json"
        self._events = deque()
        self._load()

    def add(self, event_type):
        self._events.append({"event_type": event_type, "event_timestamp": datetime.now(timezone.utc).isoformat()})
        self._save()

    def replay(self, sender):
        remaining = deque()
        while self._events:
            event = self._events.popleft()
            try:
                if isinstance(event, str):
                    sender.send(event)
                else:
                    sender.send(event["event_type"], event.get("event_timestamp"))
            except Exception:
                remaining.append(event)
        self._events = remaining
        self._save()

    def _load(self):
        if not self.path.exists():
            return
        try:
            self._events = deque(json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            self._events = deque()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(list(self._events)), encoding="utf-8")
from datetime import datetime, timezone
