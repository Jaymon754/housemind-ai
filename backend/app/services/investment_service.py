"""Transparent rental-property underwriting calculations.

All formulas are deterministic and returned with the assumptions used.  This is
an educational model, not a lending decision or investment recommendation.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ..schemas.requests import InvestmentRequest, ScenarioRequest


def _monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    if principal <= 0:
        return 0.0
    rate = annual_rate / 100 / 12
    periods = years * 12
    if rate == 0:
        return principal / periods
    return principal * rate * (1 + rate) ** periods / ((1 + rate) ** periods - 1)


def _remaining_balance(principal: float, annual_rate: float, years: int, months_paid: int) -> float:
    if principal <= 0:
        return 0.0
    rate = annual_rate / 100 / 12
    periods = years * 12
    payment = _monthly_payment(principal, annual_rate, years)
    if rate == 0:
        return max(0.0, principal - principal / periods * months_paid)
    balance = principal * (1 + rate) ** months_paid - payment * (((1 + rate) ** months_paid - 1) / rate)
    return max(0.0, balance)


def _irr(cash_flows: list[float]) -> float | None:
    """Bisection IRR; robust for conventional rental cash-flow streams."""
    def npv(rate: float) -> float:
        return sum(cf / (1 + rate) ** index for index, cf in enumerate(cash_flows))

    low, high = -0.95, 3.0
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(120):
        mid = (low + high) / 2
        value = npv(mid)
        if abs(value) < 0.01:
            return mid
        if npv(low) * value <= 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2


def underwrite(request: InvestmentRequest) -> dict[str, Any]:
    price = float(request.purchase_price)
    down_pct = request.down_payment_pct / 100
    down_payment = price * down_pct
    closing_costs = price * request.closing_cost_pct / 100
    loan = price - down_payment
    monthly_payment = _monthly_payment(loan, request.interest_rate, request.loan_term_years)
    annual_debt_service = monthly_payment * 12

    vacancy_loss = request.monthly_rent * 12 * request.vacancy_rate_pct / 100
    effective_gross_income = request.monthly_rent * 12 - vacancy_loss
    property_tax = price * request.property_tax_rate_pct / 100
    maintenance = price * request.maintenance_pct / 100
    operating_expenses = property_tax + request.insurance_annual + request.hoa_monthly * 12 + maintenance
    noi = effective_gross_income - operating_expenses
    annual_cash_flow = noi - annual_debt_service
    monthly_cash_flow = annual_cash_flow / 12
    total_cash_invested = down_payment + closing_costs
    cap_rate = noi / price * 100 if price else 0
    cash_on_cash = annual_cash_flow / total_cash_invested * 100 if total_cash_invested else 0
    dscr = noi / annual_debt_service if annual_debt_service else None
    break_even_occupancy = (operating_expenses + annual_debt_service) / max(request.monthly_rent * 12, 1) * 100
    payback = total_cash_invested / annual_cash_flow if annual_cash_flow > 0 else None

    # Multi-year hold: rent grows, operating costs grow at 2.5%, sale at the end.
    years = request.holding_years
    balance = loan
    schedule = []
    cash_flows = [-total_cash_invested]
    cumulative = -total_cash_invested
    for year in range(1, years + 1):
        rent_year = effective_gross_income * (1 + request.rent_growth_pct / 100) ** (year - 1)
        expenses_year = operating_expenses * (1.025) ** (year - 1)
        noi_year = rent_year - expenses_year
        cash_flow_year = noi_year - annual_debt_service
        cash_flows.append(cash_flow_year)
        cumulative += cash_flow_year
        months_paid = min(year * 12, request.loan_term_years * 12)
        balance = _remaining_balance(loan, request.interest_rate, request.loan_term_years, months_paid)
        schedule.append(
            {
                "year": year,
                "rent_income": round(rent_year, 0),
                "operating_expenses": round(expenses_year, 0),
                "noi": round(noi_year, 0),
                "debt_service": round(annual_debt_service, 0),
                "cash_flow": round(cash_flow_year, 0),
                "loan_balance": round(balance, 0),
                "cumulative_cash_flow": round(cumulative, 0),
            }
        )
    sale_price = price * (1 + request.appreciation_pct / 100) ** years
    selling_costs = sale_price * 0.06
    net_sale_proceeds = sale_price - selling_costs - balance
    cash_flows[-1] += net_sale_proceeds
    total_profit = sum(cash_flows)
    equity_multiple = (sum(cash_flows[1:]) + total_cash_invested) / total_cash_invested if total_cash_invested else 0
    irr = _irr(cash_flows)
    roi = total_profit / total_cash_invested * 100 if total_cash_invested else 0

    warnings = []
    if monthly_cash_flow < 0:
        warnings.append("基准情景下月现金流为负，需要持续补贴月供与持有成本。")
    if dscr is not None and dscr < 1.25:
        warnings.append(f"DSCR 为 {dscr:.2f}，低于常用的 1.25 倍风险缓冲线。")
    if cap_rate < 3:
        warnings.append("毛租金资本化率偏低，退出时的价格假设对总回报影响很大。")
    if request.vacancy_rate_pct < 3:
        warnings.append("空置率假设低于 3%，实际租赁市场可能更长。")
    if request.maintenance_pct < 0.8:
        warnings.append("维护准备金低于房价的 0.8%，可能低估老旧房屋的维修支出。")
    if break_even_occupancy > 90:
        warnings.append("盈亏平衡入住率超过 90%，抗空置能力较弱。")

    # 5×5 rent × interest sensitivity grid.
    rent_steps = np.linspace(max(0, request.monthly_rent * 0.75), request.monthly_rent * 1.25, 5)
    rate_steps = np.linspace(max(0, request.interest_rate - 2), request.interest_rate + 2, 5)
    sensitivity = []
    for rate in rate_steps:
        for rent in rent_steps:
            payment = _monthly_payment(loan, float(rate), request.loan_term_years)
            effective = float(rent) * 12 * (1 - request.vacancy_rate_pct / 100)
            cf = effective - operating_expenses - payment * 12
            sensitivity.append(
                {
                    "rent": round(float(rent), 0),
                    "rate": round(float(rate), 2),
                    "monthly_cash_flow": round(cf / 12, 0),
                    "cash_on_cash": round(cf / total_cash_invested * 100, 1) if total_cash_invested else 0,
                }
            )

    return {
        "inputs": request.model_dump(),
        "summary": {
            "purchase_price": round(price),
            "down_payment": round(down_payment),
            "closing_costs": round(closing_costs),
            "loan_amount": round(loan),
            "total_cash_invested": round(total_cash_invested),
            "monthly_mortgage": round(monthly_payment, 0),
            "annual_debt_service": round(annual_debt_service, 0),
            "effective_gross_income": round(effective_gross_income, 0),
            "operating_expenses": round(operating_expenses, 0),
            "noi": round(noi, 0),
            "annual_cash_flow": round(annual_cash_flow, 0),
            "monthly_cash_flow": round(monthly_cash_flow, 0),
        },
        "returns": {
            "cap_rate_pct": round(cap_rate, 2),
            "cash_on_cash_pct": round(cash_on_cash, 2),
            "dscr": round(dscr, 2) if dscr is not None else None,
            "break_even_occupancy_pct": round(break_even_occupancy, 1),
            "payback_years": round(payback, 1) if payback else None,
            "holding_years": years,
            "sale_price": round(sale_price),
            "net_sale_proceeds": round(net_sale_proceeds),
            "total_profit": round(total_profit),
            "total_roi_pct": round(roi, 1),
            "equity_multiple": round(equity_multiple, 2),
            "irr_pct": round(irr * 100, 1) if irr is not None else None,
            "annualized_roi_pct": round(((1 + roi / 100) ** (1 / years) - 1) * 100, 1) if roi > -100 else None,
        },
        "monthly": {
            "gross_rent": round(request.monthly_rent, 0),
            "vacancy_loss": round(vacancy_loss / 12, 0),
            "effective_rent": round(effective_gross_income / 12, 0),
            "property_tax": round(property_tax / 12, 0),
            "insurance": round(request.insurance_annual / 12, 0),
            "hoa": round(request.hoa_monthly, 0),
            "maintenance": round(maintenance / 12, 0),
            "mortgage": round(monthly_payment, 0),
            "net_cash_flow": round(monthly_cash_flow, 0),
        },
        "schedule": schedule,
        "sensitivity": sensitivity,
        "warnings": warnings,
        "verdict": {
            "label": "现金流为正" if monthly_cash_flow >= 0 else "现金流为负",
            "tone": "positive" if monthly_cash_flow >= 0 else "caution",
            "note": "投资判断应同时考虑个人税档、贷款利率、租赁法规与退出假设。",
        },
        "assumptions": [
            "等额本息贷款，利率在持有期内固定。",
            "运营费用按 2.5% 年增长；租金按输入的租金增长率增长。",
            "出售成本按成交价的 6% 估算；未计个人所得税、资本利得税与 1031 置换。",
            "空置损失、房产税、保险、HOA 与维护费按输入值计算，不含一次性大修。",
        ],
        "disclaimer": "本工具仅用于教育与分析，不构成投资、税务、法律或贷款建议。",
    }


def scenario_analysis(request: ScenarioRequest) -> dict[str, Any]:
    base = underwrite(request.base)
    rent = request.base.monthly_rent * (1 + request.rent_change_pct / 100)
    rate = max(0, request.base.interest_rate + request.interest_rate_delta)
    price = request.base.purchase_price * (1 + request.price_change_pct / 100)
    optimistic = request.base.model_copy(
        update={
            "monthly_rent": rent * 1.10,
            "interest_rate": max(0, rate - 0.5),
            "vacancy_rate_pct": max(0, request.base.vacancy_rate_pct - 2),
            "appreciation_pct": request.base.appreciation_pct + 1.0,
        }
    )
    pessimistic = request.base.model_copy(
        update={
            "monthly_rent": max(0, rent * 0.90),
            "interest_rate": rate + 1.0,
            "vacancy_rate_pct": request.base.vacancy_rate_pct + 3,
            "appreciation_pct": request.base.appreciation_pct - 2.0,
        }
    )
    custom = request.base.model_copy(
        update={"monthly_rent": rent, "interest_rate": rate, "purchase_price": price}
    )
    return {
        "base": base,
        "custom": underwrite(custom),
        "optimistic": underwrite(optimistic),
        "pessimistic": underwrite(pessimistic),
        "scenario_definitions": {
            "custom": "按用户指定的租金变化、利率变化与房价变化调整。",
            "optimistic": "租金较调整值再高 10%、空置率低 2 个百分点、利率低 0.5 个百分点、年增值高 1 个百分点。",
            "pessimistic": "租金较调整值再低 10%、空置率高 3 个百分点、利率高 1 个百分点、年增值低 2 个百分点。",
        },
    }
