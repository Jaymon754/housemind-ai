"""HouseMind AI MCP server (stdio).

Expose the same six business tools used by the web Agent through the official
Model Context Protocol SDK.  Start with:

    .venv/bin/python backend/mcp_server.py

Example client configuration (Claude Desktop / Cursor):

    {
      "mcpServers": {
        "housemind-ai": {
          "command": "/absolute/path/to/.venv/bin/python",
          "args": ["/absolute/path/to/backend/mcp_server.py"]
        }
      }
    }
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP

from backend.app.agent.tools import execute_tool

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")

mcp = FastMCP(
    "housemind-ai",
    instructions=(
        "HouseMind AI 的房产分析工具。主模型只适用于美国华盛顿州 King County 的 2014–2015 年住宅成交样本；"
        "不得把估值用于其他地区或正式信贷评估。所有投资测算均为教育性分析。"
    ),
)


@mcp.tool()
def predict_house_price(
    zipcode: str,
    sqft_living: float = 2000,
    bedrooms: int = 3,
    bathrooms: float = 2,
    sqft_lot: float = 7200,
    floors: float = 1,
    condition: int = 3,
    grade: int = 7,
    yr_built: int = 1985,
    yr_renovated: int = 0,
    waterfront: int = 0,
    view: int = 0,
    asking_price: float | None = None,
) -> dict[str, Any]:
    """预测金县住宅成交价，返回 80% 参考区间、邮编市场与主要价格驱动。"""
    result = execute_tool(
        "predict_house_price",
        {
            "zipcode": zipcode, "sqft_living": sqft_living, "bedrooms": bedrooms,
            "bathrooms": bathrooms, "sqft_lot": sqft_lot, "floors": floors,
            "condition": condition, "grade": grade, "yr_built": yr_built,
            "yr_renovated": yr_renovated, "waterfront": waterfront, "view": view,
            "asking_price": asking_price,
        },
    )
    return {"summary": result["summary"], **result["data"]}


@mcp.tool()
def explain_house_price(
    zipcode: str,
    sqft_living: float = 2000,
    bedrooms: int = 3,
    bathrooms: float = 2,
    condition: int = 3,
    grade: int = 7,
    yr_built: int = 1985,
    asking_price: float | None = None,
) -> dict[str, Any]:
    """使用 TreeSHAP 对一套房源做价格归因，并给出面积、状况、等级、翻新的反事实影响。"""
    result = execute_tool(
        "explain_house_price",
        {
            "zipcode": zipcode, "sqft_living": sqft_living, "bedrooms": bedrooms,
            "bathrooms": bathrooms, "condition": condition, "grade": grade,
            "yr_built": yr_built, "asking_price": asking_price,
        },
    )
    return {"summary": result["summary"], **result["data"]}


@mcp.tool()
def analyze_market(zipcode: str) -> dict[str, Any]:
    """查询金县邮编的中位价、单价、成交量、趋势与滨水/翻新占比。"""
    return execute_tool("analyze_market", {"zipcode": zipcode})["data"]


@mcp.tool()
def calculate_investment(
    purchase_price: float,
    monthly_rent: float,
    down_payment_pct: float = 25,
    interest_rate: float = 6.5,
    loan_term_years: int = 30,
    vacancy_rate_pct: float = 5,
    property_tax_rate_pct: float = 1.0,
    insurance_annual: float = 1800,
    hoa_monthly: float = 0,
    maintenance_pct: float = 1.0,
    appreciation_pct: float = 3.0,
    holding_years: int = 5,
) -> dict[str, Any]:
    """计算出租房月供、NOI、现金流、Cap Rate、现金回报率、DSCR、IRR 与风险提示。"""
    result = execute_tool(
        "calculate_investment",
        {
            "purchase_price": purchase_price, "monthly_rent": monthly_rent,
            "down_payment_pct": down_payment_pct, "interest_rate": interest_rate,
            "loan_term_years": loan_term_years, "vacancy_rate_pct": vacancy_rate_pct,
            "property_tax_rate_pct": property_tax_rate_pct,
            "insurance_annual": insurance_annual, "hoa_monthly": hoa_monthly,
            "maintenance_pct": maintenance_pct, "appreciation_pct": appreciation_pct,
            "holding_years": holding_years,
        },
    )
    return {"summary": result["summary"], **result["data"]}


@mcp.tool()
def search_property_knowledge(question: str, category: str | None = None) -> dict[str, Any]:
    """检索房产知识库，返回带来源 URL 的片段与引用，适合回答估值、交易、投资、税务与 AI 安全问题。"""
    result = execute_tool("search_property_knowledge", {"question": question, "category": category})
    return result["data"]


@mcp.tool()
def analyze_house_image(image_id: str) -> dict[str, Any]:
    """读取通过 Web 上传的房屋图片分析结果；需要先调用 /api/vision/upload 获得 image_id。"""
    result = execute_tool("analyze_house_image", {"image_id": image_id})
    return {"summary": result["summary"], **result["data"]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
