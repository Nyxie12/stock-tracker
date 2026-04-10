import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from ..db import SessionLocal
from ..models.user import User
from ..utils.security import JWTError, decode_access_token

log = logging.getLogger(__name__)
router = APIRouter()


async def _authenticate(websocket: WebSocket) -> User | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None
    async with SessionLocal() as db:
        return await db.get(User, user_id)


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    user = await _authenticate(websocket)
    if user is None:
        # Per RFC 6455, 1008 = policy violation. Must close *before* accept.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    manager = websocket.app.state.manager
    await manager.connect(websocket, user.id)
    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")
            symbols = msg.get("symbols") or []
            if not isinstance(symbols, list):
                await websocket.send_json({"type": "error", "message": "symbols must be a list"})
                continue
            if action == "subscribe":
                await manager.subscribe(websocket, symbols)
            elif action == "unsubscribe":
                await manager.unsubscribe(websocket, symbols)
            else:
                await websocket.send_json({"type": "error", "message": f"unknown action: {action}"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("ws loop error: %s", e)
    finally:
        await manager.disconnect(websocket)
