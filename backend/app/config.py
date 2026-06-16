from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    public_url: str
    cors_origins: tuple[str, ...]
    auto_migrate: bool
    admin_username: str
    admin_password: str
    manager_username: str
    manager_password: str
    agent_username: str
    agent_password: str
    agent_employee_id: str
    agent_employee_name: str


def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    )
    return Settings(
        database_url=os.environ.get("DATABASE_URL", ""),
        jwt_secret=os.environ.get("JWT_SECRET", ""),
        public_url=os.environ.get("PUBLIC_URL", "http://localhost:8000"),
        cors_origins=origins,
        auto_migrate=os.environ.get("AUTO_MIGRATE", "true").lower() in ("1", "true", "yes"),
        admin_username=os.environ.get("WPACS_ADMIN_USERNAME", ""),
        admin_password=os.environ.get("WPACS_ADMIN_PASSWORD", ""),
        manager_username=os.environ.get("WPACS_MANAGER_USERNAME", ""),
        manager_password=os.environ.get("WPACS_MANAGER_PASSWORD", ""),
        agent_username=os.environ.get("WPACS_AGENT_USERNAME", ""),
        agent_password=os.environ.get("WPACS_AGENT_PASSWORD", ""),
        agent_employee_id=os.environ.get("WPACS_AGENT_EMPLOYEE_ID", ""),
        agent_employee_name=os.environ.get("WPACS_AGENT_EMPLOYEE_NAME", ""),
    )
