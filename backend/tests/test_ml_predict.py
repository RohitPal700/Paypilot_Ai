"""
Tests for POST /api/ml/predict-risk.

Uses FastAPI's TestClient, which exercises the real app -- including real
Pydantic validation and the real persisted model artifact (no mocking of
the pipeline). These tests do NOT touch MongoDB, so they don't require a
live database connection: the ml router and its dependencies never import
app.db.mongodb.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.risk_policy import HIGH_THRESHOLD, LOW_THRESHOLD, probability_to_risk_tier
from app.schemas.ml import RiskTier

client = TestClient(app)

ENDPOINT = "/api/ml/predict-risk"

VALID_PAYLOAD = {
    "merchant_id": "merchant_bluewave",
    "amount": 500.0,
    "currency": "INR",
    "transaction_type": "payment",
    "payment_method": "upi",
    "category": "groceries",
    "hour": 14,
    "day_of_week": 2,
}


def test_valid_prediction_returns_200_with_expected_shape():
    response = client.post(ENDPOINT, json=VALID_PAYLOAD)
    assert response.status_code == 200

    body = response.json()
    assert "failure_probability" in body
    assert "risk_tier" in body
    assert isinstance(body["failure_probability"], float)
    assert body["risk_tier"] in {"low", "medium", "high"}


def test_probability_is_within_valid_range():
    response = client.post(ENDPOINT, json=VALID_PAYLOAD)
    assert response.status_code == 200
    probability = response.json()["failure_probability"]
    assert 0.0 <= probability <= 1.0


def test_invalid_amount_zero_is_rejected():
    payload = {**VALID_PAYLOAD, "amount": 0}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_invalid_amount_negative_is_rejected():
    payload = {**VALID_PAYLOAD, "amount": -100}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_invalid_hour_too_high_is_rejected():
    payload = {**VALID_PAYLOAD, "hour": 24}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_invalid_hour_negative_is_rejected():
    payload = {**VALID_PAYLOAD, "hour": -1}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_invalid_day_of_week_too_high_is_rejected():
    payload = {**VALID_PAYLOAD, "day_of_week": 7}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_invalid_day_of_week_negative_is_rejected():
    payload = {**VALID_PAYLOAD, "day_of_week": -1}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_invalid_transaction_type_is_rejected():
    payload = {**VALID_PAYLOAD, "transaction_type": "shopping"}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_invalid_currency_length_is_rejected():
    payload = {**VALID_PAYLOAD, "currency": "IN"}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_empty_payment_method_is_rejected():
    payload = {**VALID_PAYLOAD, "payment_method": ""}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_empty_category_is_rejected():
    payload = {**VALID_PAYLOAD, "category": ""}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_empty_merchant_id_is_rejected():
    payload = {**VALID_PAYLOAD, "merchant_id": ""}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


# --- risk-tier mapping: tested directly against the policy function, since
# the actual probability for any given request depends on model internals
# we don't want these tests coupled to. This verifies the POLICY logic
# itself is correct at and around its boundaries. ---

@pytest.mark.parametrize(
    "probability,expected_tier",
    [
        (0.0, RiskTier.LOW),
        (0.05, RiskTier.LOW),
        (LOW_THRESHOLD - 0.001, RiskTier.LOW),          # just under 0.20
        (LOW_THRESHOLD, RiskTier.MEDIUM),                # exactly 0.20 -> medium
        (0.30, RiskTier.MEDIUM),
        (HIGH_THRESHOLD - 0.001, RiskTier.MEDIUM),       # just under 0.40
        (HIGH_THRESHOLD, RiskTier.HIGH),                 # exactly 0.40 -> high
        (0.75, RiskTier.HIGH),
        (1.0, RiskTier.HIGH),
    ],
)
def test_risk_tier_mapping_boundaries(probability, expected_tier):
    assert probability_to_risk_tier(probability) == expected_tier


def test_response_risk_tier_is_consistent_with_returned_probability():
    """
    End-to-end sanity check: whatever probability the real model returns
    for a real request, the risk_tier in the same response must match what
    the policy function would independently compute for that probability.
    """
    response = client.post(ENDPOINT, json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    expected_tier = probability_to_risk_tier(body["failure_probability"])
    assert body["risk_tier"] == expected_tier.value