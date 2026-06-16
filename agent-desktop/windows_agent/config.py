from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AgentConfig:
    api_base_url: str
    username: str
    password: str
    role: str
    employee_id: str
    source: str = "windows_desktop_agent"
    heartbeat_seconds: int = 30


def load_config() -> AgentConfig:
    missing = [
        name
        for name in ("WPACS_AGENT_USERNAME", "WPACS_AGENT_PASSWORD", "WPACS_AGENT_EMPLOYEE_ID")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")
    return AgentConfig(
        api_base_url=os.environ.get("WPACS_API_BASE_URL", "http://localhost:8000").rstrip("/"),
        username=os.environ["WPACS_AGENT_USERNAME"],
        password=os.environ["WPACS_AGENT_PASSWORD"],
        role=os.environ.get("WPACS_AGENT_ROLE", "AGENT"),
        employee_id=os.environ["WPACS_AGENT_EMPLOYEE_ID"],
        source=os.environ.get("WPACS_AGENT_SOURCE", "windows_desktop_agent"),
        heartbeat_seconds=int(os.environ.get("WPACS_HEARTBEAT_SECONDS", "30")),
    )
