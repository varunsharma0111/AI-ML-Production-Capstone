"""Authenticated WebSocket router for real-time workspace job status events."""

from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.redis import RedisManager
from app.core.security import JwtVerifier
from app.db.repositories.identity import IdentityRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/v1/workspaces/{workspace_id}/jobs", tags=["websocket"])


@router.websocket("")
async def workspace_jobs_websocket(websocket: WebSocket, workspace_id: UUID) -> None:
    """Stream real-time job updates over WebSocket to authorized workspace subscribers."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication token missing")
        return

    verifier: JwtVerifier = websocket.app.state.token_verifier
    try:
        principal = verifier.verify(token)
    except Exception as exc:
        logger.warning("WebSocket authentication failed for workspace %s: %s", workspace_id, exc)
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    session_factory = websocket.app.state.session_factory
    async with session_factory() as session:
        identity_repo = IdentityRepository()
        user = await identity_repo.get_or_create_user(session, principal)
        membership = await identity_repo.get_membership(session, workspace_id, user.id)
        if membership is None:
            logger.warning(
                "WebSocket access denied for user %s to workspace %s", user.id, workspace_id
            )
            await websocket.close(code=4003, reason="Forbidden: Not a member of workspace")
            return

    await websocket.accept()
    logger.info("WebSocket connected and authenticated for workspace %s", workspace_id)

    # Send initial connection handshake event
    await websocket.send_json(
        {
            "event": "connection_established",
            "workspace_id": str(workspace_id),
            "status": "subscribed",
        }
    )

    redis_manager: RedisManager | None = getattr(websocket.app.state, "redis_manager", None)
    pubsub_task: asyncio.Task | None = None

    if redis_manager and redis_manager.is_connected:
        pubsub = redis_manager.subscribe_workspace_jobs(str(workspace_id))
        if pubsub:
            await pubsub.subscribe(f"workspace:{workspace_id}:jobs")

            async def _forward_pubsub_events() -> None:
                try:
                    async for message in pubsub.listen():
                        if message and message.get("type") == "message":
                            data_raw = message.get("data")
                            if data_raw:
                                if isinstance(data_raw, (bytes, bytearray)):
                                    data_raw = data_raw.decode("utf-8")
                                payload = json.loads(data_raw)
                                await websocket.send_json(payload)
                except asyncio.CancelledError:
                    pass
                except Exception as err:
                    logger.error("Error in WebSocket Pub/Sub listener: %s", err)
                finally:
                    await pubsub.unsubscribe(f"workspace:{workspace_id}:jobs")
                    await pubsub.close()

            pubsub_task = asyncio.create_task(_forward_pubsub_events())

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for workspace %s", workspace_id)
    finally:
        if pubsub_task:
            pubsub_task.cancel()
            try:
                await pubsub_task
            except asyncio.CancelledError:
                pass
