from fastapi import APIRouter, Depends

from app.auth.rbac import require_roles
from app.database import query


router = APIRouter(prefix="/api/v2/manager", tags=["manager"])


@router.get("/live")
def live_monitor(user=Depends(require_roles("ADMIN", "MANAGER", "SUPERVISOR"))):
    role = str(user.get("role")).upper()
    params = []
    where = ["TRUE"]
    if role == "MANAGER":
        where.append("e.manager_id = %s")
        params.append(str(user.get("user_id")))
    elif role == "SUPERVISOR":
        where.append("e.employee_id = %s")
        params.append(str(user.get("employee_id") or ""))
    rows = query(
        f"""
        SELECT e.employee_id, e.employee_name,
               COALESCE(s.current_status, 'OFFLINE') AS current_status,
               COALESCE(s.connection_status, 'OFFLINE') AS connection_status,
               COALESCE(s.shift_state, 'NOT_STARTED') AS shift_state,
               s.last_activity_at, s.last_heartbeat_at,
               COALESCE(p.productive_minutes, 0) AS productive_minutes,
               COALESCE(p.locked_minutes, 0) AS locked_minutes,
               COALESCE(p.productivity_score, 0) AS productivity_score
        FROM employees e
        LEFT JOIN agent_status s ON s.employee_id = e.employee_id
        LEFT JOIN productivity_daily p ON p.employee_id = e.employee_id AND p.date = CURRENT_DATE
        WHERE {' AND '.join(where)}
        ORDER BY e.employee_name
        """,
        tuple(params),
    )
    return {"success": True, "data": rows, "message": "OK", "errors": []}
