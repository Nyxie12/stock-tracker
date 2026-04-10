import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    manager = websocket.app.state.manager
    await manager.connect(websocket)
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
