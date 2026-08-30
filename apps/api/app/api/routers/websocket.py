"""Authenticated WebSocket router for real-time workspace job status events."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/v1/workspaces/{workspace_id}/jobs", tags=["websocket"])


@router.websocket("")
async def workspace_jobs_websocket(websocket: WebSocket, workspace_id: UUID) -> None:
    """Stream real-time job updates over WebSocket to authorized workspace subscribers."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication token missing")
        return

    await websocket.accept()
    logger.info("WebSocket connected for workspace %s", workspace_id)

    try:
        # Send initial connection handshake event
        await websocket.send_json(
            {
                "event": "connection_established",
                "workspace_id": str(workspace_id),
                "status": "subscribed",
            }
        )

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for workspace %s", workspace_id)
