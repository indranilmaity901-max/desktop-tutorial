from pathlib import Path
import os

import psycopg


ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get("DATABASE_URL")


if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is required")


with psycopg.connect(DATABASE_URL) as connection:
    with connection.cursor() as cursor:
        for path in sorted((ROOT / "database" / "migrations").glob("*.sql")):
            cursor.execute(path.read_text(encoding="utf-8"))
            print(f"Applied {path.name}")
