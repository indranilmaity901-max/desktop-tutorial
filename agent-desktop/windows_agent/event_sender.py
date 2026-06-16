from datetime import datetime, timezone
import http.cookiejar
import json
import urllib.error
import urllib.request


class EventSender:
    def __init__(self, config):
        self.config = config
        self.token = ""
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def _request(self, path, payload, token_required=True):
        headers = {"Content-Type": "application/json"}
        if token_required:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"{self.config.api_base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8")
            raise RuntimeError(f"WPACS API returned {error.code}: {body}") from error

    def authenticate(self):
        payload = self._request(
            "/api/v2/auth/login",
            {
                "username": self.config.username,
                "password": self.config.password,
                "role": self.config.role,
            },
            token_required=False,
        )
        self.token = payload["data"]["access_token"]

    def send(self, event_type):
        return self._request(
            "/api/v2/events",
            {
                "employee_id": self.config.employee_id,
                "event_type": event_type,
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "source": self.config.source,
            },
        )
