from datetime import date, timedelta
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import execute_many, execute_script


AGENTS = [
    ("EMP-001", "John Smith", "Collections", "MGR-001", "ACTIVE"),
    ("EMP-002", "Mina Patel", "Collections", "MGR-001", "ACTIVE"),
    ("EMP-003", "Avery Jones", "Support", "MGR-002", "ACTIVE"),
    ("EMP-004", "Carlos Rivera", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-005", "Emma Wilson", "Collections", "MGR-001", "ACTIVE"),
    ("EMP-006", "Noah Davis", "Collections", "MGR-001", "ACTIVE"),
    ("EMP-007", "Olivia Brown", "Collections", "MGR-001", "ACTIVE"),
    ("EMP-008", "Liam Taylor", "Collections", "MGR-001", "ACTIVE"),
    ("EMP-009", "Sophia Thomas", "Collections", "MGR-001", "ACTIVE"),
    ("EMP-010", "James White", "Collections", "MGR-001", "ACTIVE"),
    ("EMP-011", "Charlotte Moore", "Support", "MGR-002", "ACTIVE"),
    ("EMP-012", "Benjamin Martin", "Support", "MGR-002", "ACTIVE"),
    ("EMP-013", "Amelia Jackson", "Support", "MGR-002", "ACTIVE"),
    ("EMP-014", "Lucas Harris", "Support", "MGR-002", "ACTIVE"),
    ("EMP-015", "Harper Clark", "Support", "MGR-002", "ACTIVE"),
    ("EMP-016", "Ethan Lewis", "Support", "MGR-002", "ACTIVE"),
    ("EMP-017", "Evelyn Walker", "Support", "MGR-002", "ACTIVE"),
    ("EMP-018", "Alexander Hall", "Support", "MGR-002", "ACTIVE"),
    ("EMP-019", "Abigail Allen", "Support", "MGR-002", "ACTIVE"),
    ("EMP-020", "Daniel Young", "Support", "MGR-002", "ACTIVE"),
    ("EMP-021", "Grace King", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-022", "Henry Wright", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-023", "Ella Scott", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-024", "Matthew Green", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-025", "Scarlett Adams", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-026", "David Baker", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-027", "Lily Nelson", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-028", "Joseph Carter", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-029", "Hannah Mitchell", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-030", "Samuel Perez", "Compliance", "MGR-003", "ACTIVE"),
    ("EMP-031", "Victoria Roberts", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-032", "Andrew Turner", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-033", "Zoe Phillips", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-034", "Christopher Campbell", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-035", "Natalie Parker", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-036", "Ryan Evans", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-037", "Leah Edwards", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-038", "Nathan Collins", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-039", "Aubrey Stewart", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-040", "Jack Sanchez", "Sales", "MGR-004", "ACTIVE"),
    ("EMP-041", "Chloe Morris", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-042", "Gabriel Rogers", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-043", "Aria Reed", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-044", "Isaac Cook", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-045", "Madison Morgan", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-046", "Wyatt Bell", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-047", "Penelope Murphy", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-048", "Julian Bailey", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-049", "Nora Cooper", "Operations", "MGR-005", "ACTIVE"),
    ("EMP-050", "Leo Richardson", "Operations", "MGR-005", "ACTIVE"),
]
MARKED_BY = [("Admin", "admin"), ("Manager", "manager"), ("Supervisor", "supervisor")]
MANAGERS = [
    ("MGR-001", "Richard Johnson"),
    ("MGR-002", "Susan Miller"),
    ("MGR-003", "Michael Anderson"),
    ("MGR-004", "Jennifer Garcia"),
    ("MGR-005", "Robert Martinez"),
]


def main():
    execute_script((ROOT / "sql" / "schema_postgres.sql").read_text(encoding="utf-8"))
    execute_script((ROOT / "sql" / "seed_postgres.sql").read_text(encoding="utf-8"))

    random.seed(20260605)
    end_date = date(2026, 6, 5)
    dates = [end_date - timedelta(days=offset) for offset in range(29, -1, -1)]

    execute_many(
        """
        INSERT INTO managers (
          manager_id,
          manager_name
        )
        VALUES (?, ?)
        """,
        MANAGERS,
    )

    execute_many(
        """
        INSERT INTO employees (
          employee_id,
          employee_name,
          department,
          manager_id,
          status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        AGENTS,
    )

    attendance_rows = []
    productivity_rows = []
    for employee_index, employee in enumerate(AGENTS, start=1):
        employee_id = employee[0]
        performance_bias = (employee_index % 9) - 4
        for day_index, metric_date in enumerate(dates, start=1):
            selector = (employee_index * 7 + day_index * 3) % 23
            if selector == 0:
                attendance_status = "LEAVE"
                worked_minutes = 0
            elif selector in (1, 2):
                attendance_status = "ABSENT"
                worked_minutes = 0
            elif selector in (3, 4, 5):
                attendance_status = "PARTIAL"
                worked_minutes = 300 + ((employee_index + day_index) % 90)
            else:
                attendance_status = "PRESENT"
                worked_minutes = 450 + ((employee_index * 11 + day_index * 5) % 45)

            scheduled_minutes = 480
            marked_role, marked_user = MARKED_BY[(employee_index + day_index) % len(MARKED_BY)]
            date_text = metric_date.isoformat()

            attendance_rows.append((
                f"ATT-{employee_id}-{date_text}",
                employee_id,
                date_text,
                attendance_status,
                scheduled_minutes,
                worked_minutes,
                marked_role,
                marked_user,
                f"{date_text}T09:00:00Z",
            ))

            if worked_minutes == 0:
                productive_minutes = 0
                non_productive_minutes = 0
                productive_percentage = 0
            else:
                non_productive_minutes = max(20, min(160, 82 - performance_bias * 4 + ((employee_index * day_index) % 48)))
                productive_minutes = max(0, worked_minutes - non_productive_minutes)
                productive_percentage = round((productive_minutes / worked_minutes) * 100, 2)

            productivity_rows.append((
                f"PROD-{employee_id}-{date_text}",
                employee_id,
                date_text,
                productive_minutes,
                non_productive_minutes,
                productive_percentage,
                "V1_MANUAL_SEED",
            ))

    execute_many(
        """
        INSERT INTO attendance_logs (
          attendance_id,
          employee_id,
          attendance_date,
          attendance_status,
          scheduled_minutes,
          worked_minutes,
          marked_by_role,
          marked_by_user,
          created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        attendance_rows,
    )

    execute_many(
        """
        INSERT INTO productivity_logs (
          productivity_id,
          employee_id,
          metric_date,
          productive_minutes,
          non_productive_minutes,
          productive_percentage,
          source_system
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        productivity_rows,
    )

    print("Initialized PostgreSQL database from DATABASE_URL")


if __name__ == "__main__":
    main()
