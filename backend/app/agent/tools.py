"""Typed business tools shared by Function Calling, the local planner and MCP."""
from __future__ import annotations

import json
import time
from typing import Any, Callable

from pydantic import ValidationError

from ..core.security import inspect_input
from ..rag.engine import get_rag_service
from ..schemas.requests import InvestmentRequest, ValuationRequest
from ..services.investment_service import underwrite
from ..services.model_service import get_model_service
from ..services.vision_service import get_vision_service

TOOL_LABELS = {
    "predict_house_price": "房价预测",
    "explain_house_price": "价格归因",
    "analyze_market": "区域市场分析",
    "calculate_investment": "投资回报测算",
    "search_property_knowledge": "房产知识检索",
    "analyze_house_image": "房屋图片理解",
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "predict_house_price",
            "description": "使用真实训练的 XGBoost 模型预测 King County（华盛顿州金县）住宅成交价，并返回 80% 参考区间与可比房源。",
            "parameters": {
                "type": "object",
                "properties": {
                    "zipcode": {"type": "string", "description": "5 位金县邮编，例如 98052"},
                    "sqft_living": {"type": "number", "description": "室内面积，平方英尺"},
                    "bedrooms": {"type": "integer", "description": "卧室数"},
                    "bathrooms": {"type": "number", "description": "卫浴数，可含 0.5"},
                    "sqft_lot": {"type": "number", "description": "土地面积，平方英尺"},
                    "floors": {"type": "number", "description": "楼层数"},
                    "condition": {"type": "integer", "description": "房屋状况 1-5，3 为平均"},
                    "grade": {"type": "integer", "description": "建筑等级 1-13，7 为平均"},
                    "yr_built": {"type": "integer", "description": "建造年份"},
                    "yr_renovated": {"type": "integer", "description": "翻新年份，0 表示未翻新"},
                    "waterfront": {"type": "integer", "enum": [0, 1], "description": "是否滨水"},
                    "view": {"type": "integer", "description": "景观等级 0-4"},
                    "asking_price": {"type": "number", "description": "挂牌价/预算，用于判断是否处于参考区间"},
                },
                "required": ["zipcode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_house_price",
            "description": "对一套具体房源做 TreeSHAP 价格归因，说明哪些特征推高或拉低价格，并给出反事实测算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "zipcode": {"type": "string"},
                    "sqft_living": {"type": "number"},
                    "bedrooms": {"type": "integer"},
                    "bathrooms": {"type": "number"},
                    "condition": {"type": "integer"},
                    "grade": {"type": "integer"},
                    "yr_built": {"type": "integer"},
                    "asking_price": {"type": "number"},
                },
                "required": ["zipcode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_market",
            "description": "查询金县某个邮编的市场中位价、单价、成交量、样本期趋势和滨水/翻新占比。",
            "parameters": {
                "type": "object",
                "properties": {"zipcode": {"type": "string", "description": "5 位金县邮编"}},
                "required": ["zipcode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_investment",
            "description": "计算出租房的月供、NOI、现金流、Cap Rate、现金回报率、DSCR、IRR 与压力情景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "purchase_price": {"type": "number"},
                    "down_payment_pct": {"type": "number"},
                    "interest_rate": {"type": "number"},
                    "loan_term_years": {"type": "integer"},
                    "monthly_rent": {"type": "number"},
                    "vacancy_rate_pct": {"type": "number"},
                    "property_tax_rate_pct": {"type": "number"},
                    "insurance_annual": {"type": "number"},
                    "hoa_monthly": {"type": "number"},
                    "maintenance_pct": {"type": "number"},
                    "appreciation_pct": {"type": "number"},
                    "holding_years": {"type": "integer"},
                },
                "required": ["purchase_price", "monthly_rent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_property_knowledge",
            "description": "检索 HouseMind 房产知识库（估值、交易、投资、房贷、税、保险、AI 安全等），返回带来源的片段。",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "要检索的问题"},
                    "category": {"type": "string", "description": "可选分类，如 valuation/investment/mortgage"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_house_image",
            "description": "读取用户已上传房屋图片的分析结果。仅在用户上传图片或提供 image_id 时调用。",
            "parameters": {
                "type": "object",
                "properties": {"image_id": {"type": "string"}},
                "required": ["image_id"],
            },
        },
    },
]

ALIASES = {
    "area": "sqft_living",
    "living_area": "sqft_living",
    "year_built": "yr_built",
    "built_year": "yr_built",
    "beds": "bedrooms",
    "baths": "bathrooms",
    "price": "purchase_price",
    "budget": "asking_price",
    "rent": "monthly_rent",
    "down_payment": "down_payment_pct",
}


def _coerce_args(args: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in (args or {}).items():
        target = ALIASES.get(key, key)
        if target == "zipcode":
            cleaned[target] = str(value).split(".")[0].zfill(5)
            continue
        if target == "image_id":
            cleaned[target] = str(value)
            continue
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").replace("%", "").strip()
            try:
                value = float(value) if "." in value else int(value)
            except ValueError:
                pass
        cleaned[target] = value
    return cleaned


def _compact_valuation(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "estimate": result["estimate"],
        "assessment": result["assessment"],
        "market": {key: result["market"][key] for key in ["region", "median_price", "median_ppsf", "predicted_ppsf", "sales_count"]},
        "confidence": result["confidence"],
        "comparables": result["comparables"][:3],
        "top_drivers": result["explanation"]["positive"][:3],
        "top_drags": result["explanation"]["negative"][:3],
        "warnings": result["warnings"],
    }


def _tool_predict(args: dict[str, Any]) -> dict[str, Any]:
    args = _coerce_args(args)
    request = ValuationRequest(**args)
    result = get_model_service().analyze(request)
    return {
        "summary": (
            f"{request.zipcode} 的模型估值为 ${result['estimate']['value']:,}，"
            f"80% 参考区间 ${result['estimate']['range_low']:,}–${result['estimate']['range_high']:,}。"
            + (f" 挂牌价判断：{result['assessment']['verdict']}。" if result["assessment"] else "")
        ),
        "data": _compact_valuation(result),
        "artifacts": {"kind": "valuation", "id": request.zipcode},
    }


def _tool_explain(args: dict[str, Any]) -> dict[str, Any]:
    args = _coerce_args(args)
    result = get_model_service().analyze(ValuationRequest(**args))
    positives = result["explanation"]["positive"]
    negatives = result["explanation"]["negative"]
    text_bits = []
    if positives:
        text_bits.append("推高价格：" + "、".join(f"{item['label']} +${item['amount']:,.0f}" for item in positives))
    if negatives:
        text_bits.append("拉低价格：" + "、".join(f"{item['label']} ${item['amount']:,.0f}" for item in negatives))
    return {
        "summary": f"TreeSHAP 归因完成。{'；'.join(text_bits)}。",
        "data": {
            "estimate": result["estimate"],
            "base_value": result["explanation"]["base_value"],
            "contributions": result["explanation"]["contributions"][:10],
            "what_if": result["explanation"]["what_if"],
            "narrative": result["explanation"]["narrative"],
        },
        "artifacts": {"kind": "explanation"},
    }


def _tool_market(args: dict[str, Any]) -> dict[str, Any]:
    args = _coerce_args(args)
    zipcode = str(args.get("zipcode", "98052"))
    market = get_model_service().market_for_zip(zipcode)
    return {
        "summary": (
            f"{zipcode}（{market['region']}）样本中位价 ${market['median_price']:,}，"
            f"单价中位数 ${market['median_ppsf']:,.0f}/sqft，共 {market['sales_count']} 笔成交。"
        ),
        "data": {**market, "trend": market["trend"][-6:]},
        "artifacts": {"kind": "market", "id": zipcode},
    }


def _tool_investment(args: dict[str, Any]) -> dict[str, Any]:
    args = _coerce_args(args)
    request = InvestmentRequest(**args)
    result = underwrite(request)
    monthly = result["summary"]["monthly_cash_flow"]
    return {
        "summary": (
            f"月供 ${result['summary']['monthly_mortgage']:,.0f}，月现金流 ${monthly:,.0f}，"
            f"Cap Rate {result['returns']['cap_rate_pct']}%，现金回报率 {result['returns']['cash_on_cash_pct']}%，"
            f"IRR {result['returns']['irr_pct']}%。"
        ),
        "data": {
            "inputs": {
                "purchase_price": request.purchase_price,
                "monthly_rent": request.monthly_rent,
                "down_payment_pct": request.down_payment_pct,
                "interest_rate": request.interest_rate,
            },
            "summary": result["summary"],
            "returns": result["returns"],
            "monthly": result["monthly"],
            "warnings": result["warnings"],
            "verdict": result["verdict"],
        },
        "artifacts": {"kind": "investment"},
    }


def _tool_knowledge(args: dict[str, Any]) -> dict[str, Any]:
    args = _coerce_args(args)
    question = str(args.get("question", "")).strip()
    guard = inspect_input(question, 800)
    if not guard.allowed:
        return {"summary": "知识检索请求被安全策略拦截。", "data": {"results": [], "citations": []}, "artifacts": {}}
    rag = get_rag_service()
    results = rag.search(question, top_k=5, category=args.get("category"))
    citations = rag.citations(results)
    return {
        "summary": f"检索到 {len(results)} 个相关片段，最高相关来源：《{results[0]['title']}》。" if results else "未检索到相关片段。",
        "data": {
            "results": [
                {
                    "title": item["title"],
                    "section": item["section"],
                    "snippet": item["snippet"],
                    "category": item["category_label"],
                    "source_name": item["source_name"],
                    "source_url": item["source_url"],
                    "score": item["score"],
                }
                for item in results
            ],
            "citations": citations,
        },
        "artifacts": {"kind": "knowledge"},
    }


def _tool_image(args: dict[str, Any]) -> dict[str, Any]:
    image_id = str(_coerce_args(args).get("image_id", "")).strip()
    if not image_id:
        raise ValueError("缺少 image_id")
    service = get_vision_service()
    result = service.get_cached(image_id) or service.analyze(image_id)
    semantic = result["semantic"]
    return {
        "summary": (
            f"图片分析（{result['mode']}）：房间类型 {semantic.get('room_type', '未知')}，"
            f"风格 {semantic.get('style', '未知')}。仅代表可见线索。"
        ),
        "data": {
            "image_id": image_id,
            "mode": result["mode"],
            "model": result["model"],
            "features": {
                "brightness": result["features"]["brightness"],
                "temperature": result["features"]["temperature"],
                "dominant_colors": result["features"]["dominant_colors"],
                "observations": result["features"]["observations"],
            },
            "semantic": semantic,
            "disclaimer": result["disclaimer"],
        },
        "artifacts": {"kind": "vision", "id": image_id},
    }


HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "predict_house_price": _tool_predict,
    "explain_house_price": _tool_explain,
    "analyze_market": _tool_market,
    "calculate_investment": _tool_investment,
    "search_property_knowledge": _tool_knowledge,
    "analyze_house_image": _tool_image,
}


def execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name not in HANDLERS:
        raise ValueError(f"未注册的工具：{name}")
    started = time.perf_counter()
    try:
        result = HANDLERS[name](args or {})
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        result["tool"] = name
        result["label"] = TOOL_LABELS[name]
        result["arguments"] = args or {}
        return result
    except ValidationError as exc:
        raise ValueError(f"工具参数不合法：{exc.errors()[0].get('msg', 'validation error')}") from exc
    except Exception as exc:
        raise ValueError(f"{TOOL_LABELS.get(name, name)}执行失败：{type(exc).__name__}: {exc}") from exc


def tool_manifest() -> list[dict[str, Any]]:
    return [
        {
            "name": schema["function"]["name"],
            "label": TOOL_LABELS[schema["function"]["name"]],
            "description": schema["function"]["description"],
            "parameters": schema["function"]["parameters"],
        }
        for schema in TOOL_SCHEMAS
    ]
