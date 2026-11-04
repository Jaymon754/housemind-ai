"""Health, metadata, model card and security posture."""
from __future__ import annotations

import platform
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from ..agent.tools import tool_manifest
from ..core.config import settings
from ..rag.engine import get_rag_service
from ..services.model_service import get_model_service
from .deps import read_json

router = APIRouter(tags=["system"])
STARTED = time.time()


@router.get("/health")
def health() -> dict:
    model = get_model_service()
    rag = get_rag_service()
    metrics = read_json("king_county_metrics.json")
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "time": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - STARTED, 1),
        "model": {
            "loaded": True,
            "name": "XGBoost",
            "mae": metrics["models"]["xgboost"]["mae"],
            "r2": metrics["models"]["xgboost"]["r2"],
            "rows": model.artifact["training_rows"],
        },
        "rag": {"backend": rag.backend, "documents": len({c.doc_id for c in rag.chunks}), "chunks": len(rag.chunks)},
        "llm": {"mode": "deepseek" if settings.llm_enabled else "local-planner", "model": settings.deepseek_model if settings.llm_enabled else None},
        "vision": {"mode": "remote" if settings.vision_remote_enabled else "local", "model": settings.vision_model if settings.vision_remote_enabled else "Pillow feature analysis"},
    }


@router.get("/meta")
def meta() -> dict:
    model = get_model_service()
    metrics = read_json("king_county_metrics.json")
    rag = get_rag_service()
    return {
        "app": {"name": settings.app_name, "version": settings.app_version, "tagline": "以模型为估值基础，以 Agent 为决策入口"},
        "mode": {
            "llm": "deepseek" if settings.llm_enabled else "local",
            "llm_label": "DeepSeek 在线" if settings.llm_enabled else "本地编排模式",
            "vision": "remote" if settings.vision_remote_enabled else "local",
            "rag": rag.backend,
        },
        "dataset": {
            "name": "King County House Sales",
            "rows": 21_418,
            "period": model.sale_period,
            "currency": "USD",
            "target": "成交价格",
        },
        "performance": {
            "mae": metrics["models"]["xgboost"]["mae"],
            "rmse": metrics["models"]["xgboost"]["rmse"],
            "r2": metrics["models"]["xgboost"]["r2"],
            "mape": metrics["models"]["xgboost"]["mape"],
            "interval_coverage": metrics["models"]["xgboost"]["interval"]["test_coverage_pct"],
            "baseline_lift": metrics["baseline_lift_pct"],
            "best_model": metrics["best_model_label"],
        },
        "zipcodes": model.zip_options,
        "defaults": model.defaults,
        "ranges": model.ranges,
        "features": [{"key": key, "label": label} for key, label in metrics["feature_labels"].items()],
        "tools": tool_manifest(),
        "suggested_questions": [
            "预算 40 万美元，在 98052 买一套 3 室投资房，租金回报值得吗？",
            "帮我解释 98115 一套 1800 sqft、1998 年建、7 级建筑等级的房价构成。",
            "Bellevue 98004 和 Renton 98056 的市场有什么差异？",
            "什么是 DSCR？为什么它对出租房贷款很重要？",
        ],
    }


@router.get("/model-card")
def model_card() -> dict:
    card = read_json("model_card.json")
    metrics = read_json("king_county_metrics.json")
    evaluation = read_json("evaluation.json")
    generalization = read_json("generalization.json")
    return {
        "card": card,
        "metrics": metrics["models"],
        "best_model": metrics["best_model"],
        "baseline_lift_pct": metrics["baseline_lift_pct"],
        "interval": metrics["models"]["xgboost"]["interval"],
        "evaluation": evaluation,
        "generalization": generalization,
    }


@router.get("/security")
def security() -> dict:
    return {
        "guardrails": [
            {"key": "prompt_injection", "label": "提示词注入检测", "detail": "系统指令覆盖、越狱、工具越权等中英文模式"},
            {"key": "secret_protection", "label": "密钥与系统提示保护", "detail": "输入索取检测 + 输出 canary/密钥样式脱敏"},
            {"key": "tool_allowlist", "label": "工具白名单与参数校验", "detail": "6 个注册工具，Pydantic schema 与数值边界"},
            {"key": "rate_limit", "label": "请求频率限制", "detail": f"Agent {settings.agent_rate_limit} 次/分钟/IP"},
            {"key": "upload_safety", "label": "上传文件安全", "detail": "MIME/大小/像素校验，重编码去除 EXIF/GPS"},
            {"key": "output_sanitize", "label": "输出净化", "detail": "移除脚本标签、密钥样式与系统提示泄漏"},
            {"key": "responsibility", "label": "责任 AI", "detail": "估值区间、模型卡、不确定性、人工复核提示"},
        ],
        "llm_mode": "deepseek" if settings.llm_enabled else "local",
        "note": "所有防护均在服务端执行；本地模式不向第三方发送用户输入。",
    }


@router.get("/tools")
def tools() -> dict:
    return {"tools": tool_manifest(), "protocols": ["OpenAI Function Calling", "MCP"]}


@router.get("/mcp/manifest")
def mcp_manifest() -> dict:
    return {
        "protocolVersion": "2025-06-18",
        "serverInfo": {"name": "housemind-ai", "version": settings.app_version},
        "capabilities": {"tools": {}},
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["parameters"],
            }
            for tool in tool_manifest()
        ],
        "transport": {
            "stdio": "python backend/mcp_server.py",
            "http_manifest": "/api/mcp/manifest",
        },
    }


@router.get("/platform")
def platform_info() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "env": settings.env,
        "database": settings.database_url.split("://")[0],
        "mcp_enabled": settings.enable_mcp,
    }
