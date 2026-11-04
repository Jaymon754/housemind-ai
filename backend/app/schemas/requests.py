"""Validated request/response contracts for the public API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ValuationRequest(BaseModel):
    zipcode: str = Field("98052", description="King County 5-digit ZIP code")
    sqft_living: float = Field(2000, ge=300, le=12000)
    sqft_lot: float = Field(7200, ge=500, le=1_500_000)
    bedrooms: int = Field(3, ge=1, le=10)
    bathrooms: float = Field(2, ge=0.5, le=8)
    floors: float = Field(1, ge=1, le=3.5)
    condition: int = Field(3, ge=1, le=5)
    grade: int = Field(7, ge=1, le=13)
    yr_built: int = Field(1985, ge=1900, le=2015)
    yr_renovated: int = Field(0, ge=0, le=2015)
    waterfront: Literal[0, 1] = 0
    view: int = Field(0, ge=0, le=4)
    sqft_basement: float = Field(0, ge=0, le=5000)
    asking_price: float | None = Field(None, ge=10_000, le=50_000_000)
    lat: float | None = Field(None, ge=47.0, le=47.9)
    long: float | None = Field(None, ge=-122.6, le=-121.0)

    @field_validator("zipcode")
    @classmethod
    def zipcode_shape(cls, value: str) -> str:
        value = value.strip()
        if len(value) != 5 or not value.isdigit():
            raise ValueError("zipcode 必须是 5 位数字")
        return value

    @field_validator("yr_renovated")
    @classmethod
    def renovation_after_build(cls, value: int, info):
        built = info.data.get("yr_built", 1900)
        if value and value < built:
            raise ValueError("翻新年份不能早于建造年份")
        return value


class InvestmentRequest(BaseModel):
    purchase_price: float = Field(650_000, ge=50_000, le=50_000_000)
    down_payment_pct: float = Field(20, ge=0, le=100)
    interest_rate: float = Field(6.5, ge=0, le=20)
    loan_term_years: int = Field(30, ge=1, le=40)
    monthly_rent: float = Field(3_000, ge=0, le=200_000)
    vacancy_rate_pct: float = Field(5, ge=0, le=50)
    property_tax_rate_pct: float = Field(1.0, ge=0, le=10)
    insurance_annual: float = Field(1_800, ge=0, le=100_000)
    hoa_monthly: float = Field(0, ge=0, le=20_000)
    maintenance_pct: float = Field(1.0, ge=0, le=10)
    closing_cost_pct: float = Field(2.5, ge=0, le=10)
    rent_growth_pct: float = Field(3.0, ge=-10, le=20)
    appreciation_pct: float = Field(3.0, ge=-20, le=30)
    holding_years: int = Field(5, ge=1, le=30)

    @field_validator("loan_term_years", "holding_years")
    @classmethod
    def positive_years(cls, value: int) -> int:
        if value < 1:
            raise ValueError("年限必须大于 0")
        return value


class ScenarioRequest(BaseModel):
    base: InvestmentRequest
    rent_change_pct: float = Field(0, ge=-50, le=100)
    interest_rate_delta: float = Field(0, ge=-5, le=8)
    price_change_pct: float = Field(0, ge=-40, le=60)


class AgentRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=2000)
    conversation_id: str | None = Field(None, max_length=36)
    image_id: str | None = Field(None, max_length=80)

    @field_validator("message")
    @classmethod
    def clean_control_chars(cls, value: str) -> str:
        cleaned = "".join(char for char in value if char == "\n" or char == "\t" or ord(char) >= 32)
        return cleaned.strip()


class KnowledgeQuery(BaseModel):
    question: str = Field(..., min_length=2, max_length=800)
    top_k: int = Field(6, ge=3, le=10)
    category: str | None = Field(None, max_length=40)


class VisionFeedback(BaseModel):
    label: str = Field(..., max_length=80)
    correct: bool


class ReportRequest(BaseModel):
    kind: Literal["valuation", "investment", "agent"] = "valuation"
    payload: dict = Field(default_factory=dict)
    title: str = Field("HouseMind AI 分析报告", max_length=120)
