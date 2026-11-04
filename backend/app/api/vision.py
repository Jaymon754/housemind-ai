"""Image upload, analysis and protected image serving."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..services.vision_service import VisionError, get_vision_service
from .deps import enforce_rate

router = APIRouter(prefix="/vision", tags=["vision"])


class AnalyzeBody(BaseModel):
    image_id: str = Field(..., min_length=6, max_length=40)


@router.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)) -> dict:
    enforce_rate(request, "vision", limit=20)
    content = await file.read()
    try:
        return get_vision_service().ingest(content, file.content_type or "", file.filename or "upload.jpg")
    except VisionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analyze")
def analyze(payload: AnalyzeBody) -> dict:
    try:
        return get_vision_service().analyze(payload.image_id)
    except VisionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/images/{image_id}")
def image(image_id: str, variant: str | None = None):
    try:
        path = get_vision_service().get_image_path(image_id, variant)
    except VisionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})
