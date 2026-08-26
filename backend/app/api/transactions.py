from fastapi import APIRouter, HTTPException

from app.schemas.transaction import Transaction, TransactionCreate
from app.services.transaction_service import (
    create_transaction,
    create_transactions_bulk,
    get_all_transactions,
    get_transaction_by_id,
)
from app.utils.synthetic_data import generate_synthetic_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", response_model=Transaction)
def add_transaction(payload: TransactionCreate):
    """
    Create a new transaction.
    Pydantic validates `payload` against TransactionCreate before this
    function even runs (e.g. rejects a negative amount or an invalid
    transaction_type/status automatically).
    """
    transaction = Transaction(**payload.model_dump())
    create_transaction(transaction)
    return transaction


@router.get("", response_model=list[Transaction])
def list_transactions():
    """Return all transactions currently stored in MongoDB."""
    return get_all_transactions()


@router.post("/seed")
def seed_transactions():
    """
    Generate ~50 realistic synthetic transactions and insert them into
    MongoDB. Intended for local development/testing only.
    """
    synthetic_transactions = generate_synthetic_transactions(count=50)
    inserted_count = create_transactions_bulk(synthetic_transactions)
    return {"inserted": inserted_count}


@router.get("/{transaction_id}", response_model=Transaction)
def get_transaction(transaction_id: str):
    """Return a single transaction by its transaction_id, or 404 if not found."""
    transaction = get_transaction_by_id(transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction