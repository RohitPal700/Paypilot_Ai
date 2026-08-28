"""
Tests for the analytics endpoints (summary, by-status, by-type,
by-category, by-date).

Same approach as test_transactions.py: the MongoDB aggregation calls in
app/services/analytics_service.py are replaced at the point
app/api/analytics.py calls them, so no real database is needed -- only the
routing/response-shaping logic is under test here.
"""

import app.api.analytics as analytics_api
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analytics_summary_returns_expected_shape(monkeypatch):
    fake_summary = {
        "total_transactions": 53,
        "total_successful_amount": 49164.45,
        "total_failed_count": 4,
        "total_refund_amount": 11108.19,
    }
    monkeypatch.setattr(analytics_api, "get_summary", lambda: fake_summary)

    response = client.get("/api/analytics/summary")
    assert response.status_code == 200
    assert response.json() == fake_summary


def test_analytics_by_status_returns_wrapped_results(monkeypatch):
    fake_counts = [
        {"status": "successful", "count": 45},
        {"status": "failed", "count": 4},
        {"status": "pending", "count": 4},
    ]
    monkeypatch.setattr(analytics_api, "get_count_by_status", lambda: fake_counts)

    response = client.get("/api/analytics/by-status")
    assert response.status_code == 200
    assert response.json() == {"results": fake_counts}


def test_analytics_by_type_returns_wrapped_results(monkeypatch):
    fake_counts = [
        {"transaction_type": "payment", "count": 37},
        {"transaction_type": "refund", "count": 8},
    ]
    monkeypatch.setattr(analytics_api, "get_count_by_type", lambda: fake_counts)

    response = client.get("/api/analytics/by-type")
    assert response.status_code == 200
    assert response.json() == {"results": fake_counts}


def test_analytics_by_category_returns_wrapped_results(monkeypatch):
    fake_categories = [
        {"category": "groceries", "total_amount": 1200.50, "count": 10},
        {"category": "travel", "total_amount": 5400.00, "count": 3},
    ]
    monkeypatch.setattr(analytics_api, "get_summary_by_category", lambda: fake_categories)

    response = client.get("/api/analytics/by-category")
    assert response.status_code == 200
    assert response.json() == {"results": fake_categories}


def test_analytics_by_date_returns_wrapped_results(monkeypatch):
    fake_dates = [
        {"date": "2026-08-25", "total_amount": 61934.91, "count": 53},
    ]
    monkeypatch.setattr(analytics_api, "get_summary_by_date", lambda: fake_dates)

    response = client.get("/api/analytics/by-date")
    assert response.status_code == 200
    assert response.json() == {"results": fake_dates}


def test_analytics_by_status_returns_empty_list_when_no_data(monkeypatch):
    monkeypatch.setattr(analytics_api, "get_count_by_status", lambda: [])

    response = client.get("/api/analytics/by-status")
    assert response.status_code == 200
    assert response.json() == {"results": []}