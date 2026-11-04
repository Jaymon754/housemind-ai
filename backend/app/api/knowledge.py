"""RAG search, answer and document library endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..core.config import settings
from ..rag.engine import get_rag_service
from ..schemas.requests import KnowledgeQuery
from .deps import enforce_rate

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/stats")
def stats() -> dict:
    return get_rag_service().stats()


@router.post("/search")
def search(payload: KnowledgeQuery, request: Request) -> dict:
    enforce_rate(request, "knowledge", limit=60)
    rag = get_rag_service()
    results = rag.search(payload.question, top_k=payload.top_k, category=payload.category)
    return {"question": payload.question, "results": results, "citations": rag.citations(results)}


@router.post("/query")
def query(payload: KnowledgeQuery, request: Request) -> dict:
    enforce_rate(request, "knowledge", limit=30)
    return get_rag_service().answer(payload.question, top_k=payload.top_k, category=payload.category)


@router.get("/documents/{doc_id}")
def document(doc_id: str) -> dict:
    if not doc_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="非法文档 ID")
    path = settings.knowledge_dir / f"{doc_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="文档不存在")
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            body = parts[2].strip()
    return {"doc_id": doc_id, "meta": meta, "markdown": body}
