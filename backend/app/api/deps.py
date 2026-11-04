"""Shared API helpers."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from ..core.config import settings
from ..core.security import rate_limiter


@lru_cache(maxsize=32)
def read_json(name: str) -> dict[str, Any]:
    path: Path = settings.artifact_dir / name
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"分析产物缺失：{name}。请先运行 ml/train.py。")
    return json.loads(path.read_text(encoding="utf-8"))


def client_key(request: Request, scope: str) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    host = forwarded or (request.client.host if request.client else "unknown")
    return f"{scope}:{host}"


def enforce_rate(request: Request, scope: str, limit: int | None = None, window: int = 60) -> None:
    allowed, retry = rate_limiter.check(client_key(request, scope), limit or settings.agent_rate_limit, window)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"请求过于频繁，请 {retry} 秒后再试。")
