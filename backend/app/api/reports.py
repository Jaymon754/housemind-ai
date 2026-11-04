"""Saved analyses for printable investment reports."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..core.database import SavedAnalysis, SessionLocal, init_db
from ..schemas.requests import ReportRequest

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
def save(payload: ReportRequest) -> dict:
    init_db()
    db = SessionLocal()
    try:
        item = SavedAnalysis(
            id=str(uuid.uuid4()),
            kind=payload.kind,
            title=payload.title,
            payload=payload.payload,
        )
        db.add(item)
        db.commit()
        return {"id": item.id, "created_at": item.created_at.isoformat()}
    finally:
        db.close()


@router.get("")
def list_reports() -> dict:
    init_db()
    db = SessionLocal()
    try:
        rows = db.scalars(select(SavedAnalysis).order_by(SavedAnalysis.created_at.desc()).limit(30)).all()
        return {
            "items": [
                {"id": row.id, "kind": row.kind, "title": row.title, "created_at": row.created_at.isoformat()}
                for row in rows
            ]
        }
    finally:
        db.close()


@router.get("/{report_id}")
def get_report(report_id: str) -> dict:
    db = SessionLocal()
    try:
        row = db.get(SavedAnalysis, report_id)
        if not row:
            raise HTTPException(status_code=404, detail="报告不存在")
        return {
            "id": row.id,
            "kind": row.kind,
            "title": row.title,
            "payload": row.payload,
            "created_at": row.created_at.isoformat(),
        }
    finally:
        db.close()
