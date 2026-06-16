from fastapi import APIRouter, Depends, HTTPException

from app.auth.rbac import can_access_employee, require_roles
from app.database import query


router = APIRouter(prefix="/api/v2/agent", tags=["agent"])


@router.get("/status")
def agent_status(employee_id: str | None = None, user=Depends(require_roles("ADMIN", "MANAGER", "SUPERVISOR", "AGENT"))):
    role = str(user.get("role")).upper()
    target = employee_id or user.get("employee_id")
    params = []
    where = ["TRUE"]
    if target:
        if not can_access_employee(user, str(target)):
            raise HTTPException(status_code=403, detail="Access denied")
        where.append("e.employee_id = %s")
        params.append(str(target))
    elif role == "MANAGER":
        where.append("e.manager_id = %s")
        params.append(str(user.get("user_id")))
    elif role in {"SUPERVISOR", "AGENT"}:
        where.append("FALSE")
    rows = query(
        f"""
        SELECT e.employee_id, e.employee_name, e.department, e.manager_id,
               COALESCE(s.current_status, 'OFFLINE') AS current_status,
               COALESCE(s.shift_state, 'NOT_STARTED') AS shift_state,
               s.last_event_type, s.last_activity_at, s.last_heartbeat_at,
               COALESCE(s.connection_status, 'OFFLINE') AS connection_status,
               s.updated_at
        FROM employees e
        LEFT JOIN agent_status s ON s.employee_id = e.employee_id
        WHERE {' AND '.join(where)}
        ORDER BY e.employee_name
        """,
        tuple(params),
    )
    return {"success": True, "data": rows, "message": "OK", "errors": []}
