from __future__ import annotations

import pytest

from backend.app.schemas.requests import InvestmentRequest
from backend.app.services.investment_service import underwrite


def test_zero_interest_loan_and_dscr():
    request = InvestmentRequest(
        purchase_price=400_000,
        down_payment_pct=25,
        interest_rate=0,
        loan_term_years=30,
        monthly_rent=2_500,
        vacancy_rate_pct=0,
        property_tax_rate_pct=0,
        insurance_annual=0,
        maintenance_pct=0,
    )
    result = underwrite(request)
    summary = result["summary"]
    assert summary["loan_amount"] == 300_000
    assert summary["monthly_mortgage"] == pytest.approx(833, abs=1)
    assert summary["annual_debt_service"] == pytest.approx(10_000, abs=1)
    assert summary["noi"] == pytest.approx(30_000, abs=0.1)
    assert result["returns"]["dscr"] == pytest.approx(30_000 / (summary["monthly_mortgage"] * 12), rel=0.01)


def test_full_cash_purchase_has_no_debt_service():
    request = InvestmentRequest(
        purchase_price=300_000,
        down_payment_pct=100,
        interest_rate=7,
        monthly_rent=2_000,
        vacancy_rate_pct=0,
        property_tax_rate_pct=0,
        insurance_annual=0,
        maintenance_pct=0,
    )
    result = underwrite(request)
    assert result["summary"]["loan_amount"] == 0
    assert result["summary"]["monthly_mortgage"] == 0
    assert result["returns"]["dscr"] is None or result["returns"]["dscr"] > 0


def test_negative_cash_flow_is_flagged():
    request = InvestmentRequest(purchase_price=900_000, monthly_rent=2_000, down_payment_pct=10)
    result = underwrite(request)
    assert result["summary"]["monthly_cash_flow"] < 0
    assert result["warnings"]
    assert result["verdict"]["tone"] in {"negative", "caution", "positive"}
    assert result["verdict"]["label"]
