"""WebSocket：实时推送 worker 线程产生的日志/二维码/状态事件。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.event_bus import bus
from app.web_auth import SESSION_COOKIE, get_session

router = APIRouter(tags=["ws"])


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    session = get_session(ws.cookies.get(SESSION_COOKIE))
    if session is None or session.must_change_password:
        await ws.close(code=4401)
        return
    await ws.accept()
    q = bus.subscribe()
    try:
        while True:
            data = await q.get()
            await ws.send_text(data)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        bus.unsubscribe(q)
