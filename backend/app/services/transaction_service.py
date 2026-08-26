from typing import List, Optional

from app.db.mongodb import db
from app.schemas.transaction import Transaction

# Reuses the existing MongoDB connection (app/db/mongodb.py).
# This just points at the "transactions" collection inside that same database.
collection = db["transactions"]


def create_transaction(transaction: Transaction) -> None:
    """Insert one transaction document into the transactions collection."""
    collection.insert_one(transaction.model_dump())


def create_transactions_bulk(transactions: List[Transaction]) -> int:
    """Insert many transaction documents at once (used by the seed endpoint)."""
    if not transactions:
        return 0
    documents = [t.model_dump() for t in transactions]
    result = collection.insert_many(documents)
    return len(result.inserted_ids)


def get_all_transactions() -> List[dict]:
    """
    Fetch all transactions from MongoDB.
    Excludes MongoDB's internal _id field since it isn't part of our schema
    and isn't JSON-serializable by default.
    """
    return list(collection.find({}, {"_id": 0}))


def get_transaction_by_id(transaction_id: str) -> Optional[dict]:
    """Fetch a single transaction by its transaction_id field."""
    return collection.find_one({"transaction_id": transaction_id}, {"_id": 0})