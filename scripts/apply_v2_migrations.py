from pathlib import Path
import os
import sys

import psycopg


ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get("DATABASE_URL")
sys.path.insert(0, str(ROOT / "backend"))


if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is required")


with psycopg.connect(DATABASE_URL) as connection:
    with connection.cursor() as cursor:
        for path in sorted((ROOT / "database" / "migrations").glob("*.sql")):
            cursor.execute(path.read_text(encoding="utf-8"))
            print(f"Applied {path.name}")

from app.database import verify_schema
from app.services.seed import seed_from_environment

schema = verify_schema()
if schema["missing_tables"]:
    raise SystemExit(f"Missing required tables: {', '.join(schema['missing_tables'])}")
seeded = seed_from_environment()
print(f"Verified tables: {', '.join(schema['present_tables'])}")
print(f"Verified indexes: {', '.join(schema['present_indexes'])}")
print(f"Seeded identities: {', '.join(seeded) if seeded else 'none'}")
