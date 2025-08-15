from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..utils.connection_manager import ConnectionManager
from ..services.token_auth import get_current_user_ws

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/notifications")
async def notifications(websocket: WebSocket):
    user = await get_current_user_ws(websocket)
    if not user:
        return
    channel = f"notifications-{user}"

    await manager.connect(websocket, channel)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
