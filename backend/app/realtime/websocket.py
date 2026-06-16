from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.rbac import can_access_employee
from app.auth.jwt import verify_token


router = APIRouter()
connections: dict[WebSocket, dict] = {}


async def broadcast(message: dict):
    dead = []
    for websocket in list(connections):
        user = connections.get(websocket) or {}
        employee_id = (message.get("payload") or {}).get("employee_id")
        if employee_id and not can_access_employee(user, str(employee_id)):
            continue
        try:
            await websocket.send_json(message)
        except Exception:
            dead.append(websocket)
    for websocket in dead:
        connections.pop(websocket, None)


@router.websocket("/api/v2/live")
async def live(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    try:
        user = verify_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    connections[websocket] = user
    try:
        await websocket.send_json({"type": "connected", "payload": {"role": user.get("role")}})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.pop(websocket, None)
