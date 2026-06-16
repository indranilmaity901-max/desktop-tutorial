from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    public_url: str
    cors_origins: tuple[str, ...]


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
    )
