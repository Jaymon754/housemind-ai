from __future__ import annotations

import math

import pytest


def test_health_and_meta(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["model"]["loaded"] is True
    assert body["model"]["mae"] > 0
    assert body["rag"]["documents"] >= 18

    meta = client.get("/api/meta").json()
    assert meta["dataset"]["name"] == "King County House Sales"
    assert meta["performance"]["mae"] > 0
    assert meta["mode"]["llm"] in {"local", "deepseek"}
    assert len(meta["tools"]) == 6


def test_valuation_endpoint(client, valuation_payload):
    response = client.post("/api/valuation/analyze", json=valuation_payload)
    assert response.status_code == 200, response.text
    data = response.json()
    estimate = data["estimate"]
    assert 100_000 < estimate["value"] < 2_000_000
    assert estimate["range_low"] < estimate["value"] < estimate["range_high"]
    assert estimate["price_per_sqft"] > 0
    assert data["confidence"]["score"] >= 50
    assert data["comparables"]
    assert data["market"]["zipcode"] == "98115"

    explanation = data["explanation"]
    total = explanation["base_value"] + sum(item["amount"] for item in explanation["contributions"])
    assert math.isclose(total, explanation["prediction"], rel_tol=1e-6, abs_tol=2.0)


def test_valuation_assessment_and_validation(client, valuation_payload):
    data = client.post("/api/valuation/analyze", json=valuation_payload).json()
    assert data["assessment"] is not None
    assert data["assessment"]["tone"] in {"low", "fair", "high"}
    assert data["assessment"]["verdict"]

    bad = dict(valuation_payload, zipcode="123")
    assert client.post("/api/valuation/analyze", json=bad).status_code == 422

    bad = dict(valuation_payload, yr_renovated=1950)
    assert client.post("/api/valuation/analyze", json=bad).status_code == 422


def test_investment_endpoint(client):
    response = client.post("/api/investment/calculate", json={})
    assert response.status_code == 200, response.text
    data = response.json()
    summary = data["summary"]
    returns = data["returns"]
    assert summary["monthly_mortgage"] > 0
    assert summary["annual_debt_service"] == pytest.approx(summary["monthly_mortgage"] * 12, abs=6)
    assert returns["cap_rate_pct"] == round(summary["noi"] / summary["purchase_price"] * 100, 2)
    assert returns["dscr"] == round(summary["noi"] / summary["annual_debt_service"], 2)
    assert len(data["schedule"]) == 5
    assert len(data["sensitivity"]) >= 9


def test_investment_scenarios(client):
    response = client.post("/api/investment/scenarios", json={"base": {}, "rent_change_pct": -10})
    assert response.status_code == 200
    data = response.json()
    assert {"base", "custom", "optimistic", "pessimistic"} <= set(data)
    assert data["pessimistic"]["summary"]["monthly_cash_flow"] <= data["base"]["summary"]["monthly_cash_flow"]
    assert data["optimistic"]["summary"]["monthly_cash_flow"] >= data["base"]["summary"]["monthly_cash_flow"]


def test_knowledge_query_and_search(client):
    data = client.post("/api/knowledge/query", json={"question": "首付比例和DSCR有什么关系？", "top_k": 6}).json()
    assert data["mode"].startswith("local")
    assert len(data["citations"]) >= 3
    assert "DSCR" in data["answer"]
    sections = {item["section"] for item in data["results"]}
    assert any("DSCR" in section for section in sections)
    assert all(item["source_url"].startswith("http") for item in data["citations"])

    search = client.post("/api/knowledge/search", json={"question": "1031 置换 条件", "top_k": 5}).json()
    assert search["results"]
    assert any("1031" in item["title"] or "1031" in item["snippet"] for item in search["results"])


def test_knowledge_stats_and_document(client):
    stats = client.get("/api/knowledge/stats").json()
    assert stats["documents"] == 18
    assert stats["chunks"] >= 60
    assert stats["categories"]
    doc_id = stats["documents_list"][0]["doc_id"]
    doc = client.get(f"/api/knowledge/documents/{doc_id}")
    assert doc.status_code == 200
    assert doc.json()["markdown"].startswith("#")


def test_dashboard_and_research(client):
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["overview"]["total_sales"] == 21_418
    assert dashboard["map_points"]
    assert dashboard["top_zipcodes"]
    assert dashboard["quality"]["raw_rows"] == 21_613

    research = client.get("/api/research").json()
    assert research["king_county"]["best_model"] == "xgboost"
    assert research["king_county"]["interval"]["test_coverage_pct"] > 75
    assert research["generalization"]["unseen_zipcodes"]
    assert len(research["shap"]["ranking"]) >= 10
    assert "california" in research and "uci" in research


def test_reports_roundtrip(client):
    payload = {"kind": "valuation", "title": "测试报告", "payload": {"note": "api test"}}
    created = client.post("/api/reports", json=payload)
    assert created.status_code in {200, 201}, created.text
    report_id = created.json()["id"]
    listing = client.get("/api/reports").json()
    assert any(item["id"] == report_id for item in listing["items"])
    assert client.get(f"/api/reports/{report_id}").json()["title"] == "测试报告"
