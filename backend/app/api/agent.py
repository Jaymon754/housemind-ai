"""Agent streaming and conversation history endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..agent.orchestrator import get_orchestrator
from ..schemas.requests import AgentRequest
from .deps import enforce_rate

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/stream")
async def stream(payload: AgentRequest, request: Request):
    enforce_rate(request, "agent", limit=30)
    orchestrator = get_orchestrator()

    async def generator():
        async for chunk in orchestrator.stream(
            payload.message,
            conversation_id=payload.conversation_id,
            image_id=payload.image_id,
        ):
            yield chunk

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/conversations")
def conversations() -> dict:
    return {"items": get_orchestrator().list_conversations()}


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str) -> dict:
    data = get_orchestrator().history(conversation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return data
