from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.rbac import can_access_employee, require_roles
from app.database import query, query_one
from app.events.processor import parse_timestamp, process_event
from app.realtime.websocket import broadcast
from app.services.audit import audit


router = APIRouter(prefix="/api/v2/events", tags=["events"])


class EventIn(BaseModel):
    employee_id: str
    event_type: str
    event_timestamp: str | None = None
    source: str = "api"


@router.post("")
async def create_event(payload: EventIn, user=Depends(require_roles("ADMIN", "MANAGER", "SUPERVISOR", "AGENT"))):
    role = str(user.get("role")).upper()
    if role == "SUPERVISOR":
        raise HTTPException(status_code=403, detail="Supervisors are read-only")
    if role == "AGENT" and str(user.get("employee_id") or "") != payload.employee_id:
        raise HTTPException(status_code=403, detail="Agents may only send their own events")
    if not can_access_employee(user, payload.employee_id):
        raise HTTPException(status_code=403, detail="Access denied for this employee")
    if not query_one("SELECT employee_id FROM employees WHERE employee_id = %s", (payload.employee_id,)):
        raise HTTPException(status_code=400, detail="Employee not found")
    try:
        result = process_event(
            payload.employee_id,
            payload.event_type,
            parse_timestamp(payload.event_timestamp),
            payload.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit(str(user.get("username")), "Status Changed", payload.employee_id, f"{payload.event_type} from {payload.source}")
    await broadcast({"type": "workstation_event", "payload": result["event"]})
    await broadcast({"type": "agent_status", "payload": result["status"]})
    await broadcast({"type": "productivity", "payload": result["productivity"]})
    return {"success": True, "data": result, "message": "Event saved", "errors": []}


@router.get("")
def list_events(
    employee_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(require_roles("ADMIN", "MANAGER", "SUPERVISOR", "AGENT")),
):
    params = []
    where = ["TRUE"]
    role = str(user.get("role")).upper()
    if employee_id:
        if not can_access_employee(user, employee_id):
            raise HTTPException(status_code=403, detail="Access denied for this employee")
        where.append("e.employee_id = %s")
        params.append(employee_id)
    elif role == "MANAGER":
        where.append("e.manager_id = %s")
        params.append(str(user.get("user_id")))
    elif role in {"SUPERVISOR", "AGENT"}:
        where.append("e.employee_id = %s")
        params.append(str(user.get("employee_id") or ""))
    params.append(limit)
    rows = query(
        f"""
        SELECT w.id, w.employee_id, e.employee_name, w.event_type,
               w.event_timestamp, w.source, w.created_at
        FROM workstation_events w
        JOIN employees e ON e.employee_id = w.employee_id
        WHERE {' AND '.join(where)}
        ORDER BY w.event_timestamp DESC, w.id DESC
        LIMIT %s
        """,
        tuple(params),
    )
    return {"success": True, "data": rows, "message": "OK", "errors": []}
