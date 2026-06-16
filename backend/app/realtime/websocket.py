from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()
connections: set[WebSocket] = set()


async def broadcast(message: dict):
    dead = []
    for websocket in list(connections):
        try:
            await websocket.send_json(message)
        except Exception:
            dead.append(websocket)
    for websocket in dead:
        connections.discard(websocket)


@router.websocket("/api/v2/live")
async def live(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    try:
        await websocket.send_json({"type": "connected", "payload": {}})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)
