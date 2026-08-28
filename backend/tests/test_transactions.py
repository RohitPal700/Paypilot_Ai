"""
Tests for the transaction endpoints (create, list, lookup/404) and for
TransactionCreate's Pydantic validation.

These are unit-style tests: the actual MongoDB calls inside
app/services/transaction_service.py are replaced (via monkeypatch) at the
point app/api/transactions.py calls them, so no real database connection
is required. Only the request validation, response shaping, and routing
logic are under test here -- not MongoDB itself.
"""

from datetime import datetime, timezone

import app.api.transactions as transactions_api
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ENDPOINT = "/api/transactions"

VALID_PAYLOAD = {
    "merchant_id": "merchant_bluewave",
    "amount": 250.0,
    "currency": "INR",
    "transaction_type": "payment",
    "status": "successful",
    "payment_method": "upi",
    "customer_id": "customer_1234",
    "category": "groceries",
}


# --- Validation ---

def test_create_transaction_rejects_negative_amount(monkeypatch):
    monkeypatch.setattr(transactions_api, "create_transaction", lambda t: None)
    payload = {**VALID_PAYLOAD, "amount": -500}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_create_transaction_rejects_zero_amount(monkeypatch):
    monkeypatch.setattr(transactions_api, "create_transaction", lambda t: None)
    payload = {**VALID_PAYLOAD, "amount": 0}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_create_transaction_rejects_invalid_transaction_type(monkeypatch):
    monkeypatch.setattr(transactions_api, "create_transaction", lambda t: None)
    payload = {**VALID_PAYLOAD, "transaction_type": "shopping"}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_create_transaction_rejects_invalid_status(monkeypatch):
    monkeypatch.setattr(transactions_api, "create_transaction", lambda t: None)
    payload = {**VALID_PAYLOAD, "status": "cancelled"}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_create_transaction_rejects_invalid_currency_length(monkeypatch):
    monkeypatch.setattr(transactions_api, "create_transaction", lambda t: None)
    payload = {**VALID_PAYLOAD, "currency": "IN"}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_create_transaction_rejects_missing_required_field(monkeypatch):
    monkeypatch.setattr(transactions_api, "create_transaction", lambda t: None)
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "merchant_id"}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


# --- Creation ---

def test_create_transaction_valid_payload_returns_200_with_server_fields(monkeypatch):
    captured = {}

    def fake_create_transaction(transaction):
        captured["transaction"] = transaction  # simulate a successful insert

    monkeypatch.setattr(transactions_api, "create_transaction", fake_create_transaction)

    response = client.post(ENDPOINT, json=VALID_PAYLOAD)
    assert response.status_code == 200

    body = response.json()
    # Server-generated fields must be present even though the client didn't send them.
    assert "transaction_id" in body and body["transaction_id"]
    assert "created_at" in body and body["created_at"]
    # Client-supplied fields should be echoed back unchanged.
    assert body["merchant_id"] == VALID_PAYLOAD["merchant_id"]
    assert body["amount"] == VALID_PAYLOAD["amount"]
    # The service layer should have actually been called with a Transaction.
    assert "transaction" in captured


# --- Lookup / 404 ---

def test_get_transaction_by_id_found_returns_200(monkeypatch):
    stored = {
        **VALID_PAYLOAD,
        "transaction_id": "txn-123",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    monkeypatch.setattr(transactions_api, "get_transaction_by_id", lambda tid: stored)

    response = client.get(f"{ENDPOINT}/txn-123")
    assert response.status_code == 200
    assert response.json()["transaction_id"] == "txn-123"


def test_get_transaction_by_id_not_found_returns_404(monkeypatch):
    monkeypatch.setattr(transactions_api, "get_transaction_by_id", lambda tid: None)

    response = client.get(f"{ENDPOINT}/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"


# --- Listing ---

def test_list_transactions_returns_all_items(monkeypatch):
    stored = [
        {
            **VALID_PAYLOAD,
            "transaction_id": "txn-1",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            **VALID_PAYLOAD,
            "transaction_id": "txn-2",
            "amount": 999.99,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    monkeypatch.setattr(transactions_api, "get_all_transactions", lambda: stored)

    response = client.get(ENDPOINT)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {t["transaction_id"] for t in body} == {"txn-1", "txn-2"}


def test_list_transactions_returns_empty_list_when_no_data(monkeypatch):
    monkeypatch.setattr(transactions_api, "get_all_transactions", lambda: [])

    response = client.get(ENDPOINT)
    assert response.status_code == 200
    assert response.json() == []