from app.database import execute


def audit(actor: str, action: str, target: str, details: str = ""):
    execute(
        """
        INSERT INTO audit_log (actor, action, target, details)
        VALUES (%s, %s, %s, %s)
        """,
        (actor, action, target, details),
    )
