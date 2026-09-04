"""Analytics over the currently selected uploaded statement."""

from app.db.mongodb import db

collection = db["transactions"]

REAL_DATA_FILTER = {"source": "statement_import"}
OUTGOING_SPEND_FILTER = {
    **REAL_DATA_FILTER,
    "status": "successful",
    "transaction_type": {"$in": ["payment", "expense"]},
}


def _filter(statement_id: str | None = None) -> dict:
    result = dict(REAL_DATA_FILTER)
    if statement_id:
        result["statement_id"] = statement_id
    return result


def get_summary(statement_id: str | None = None) -> dict:
    base_match = _filter(statement_id)
    total_transactions = collection.count_documents(base_match)

    successful = list(collection.aggregate([
        {"$match": {**base_match, "status": "successful"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    spent = list(collection.aggregate([
        {"$match": {**base_match, "status": "successful", "transaction_type": {"$in": ["payment", "expense"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    refunds = list(collection.aggregate([
        {"$match": {**base_match, "transaction_type": "refund", "status": "successful"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))

    return {
        "total_transactions": total_transactions,
        "total_spent_amount": spent[0]["total"] if spent else 0.0,
        "total_successful_amount": successful[0]["total"] if successful else 0.0,
        "total_failed_count": collection.count_documents({**base_match, "status": "failed"}),
        "total_refund_amount": refunds[0]["total"] if refunds else 0.0,
    }


def get_count_by_status(statement_id: str | None = None) -> list[dict]:
    results = collection.aggregate([
        {"$match": _filter(statement_id)},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ])
    return [{"status": r["_id"], "count": r["count"]} for r in results]


def get_count_by_type(statement_id: str | None = None) -> list[dict]:
    results = collection.aggregate([
        {"$match": _filter(statement_id)},
        {"$group": {"_id": "$transaction_type", "count": {"$sum": 1}}},
    ])
    return [{"transaction_type": r["_id"], "count": r["count"]} for r in results]


def get_summary_by_category(statement_id: str | None = None) -> list[dict]:
    # This is a spending report, so received/refunded money and failed or
    # pending transactions must never appear as spending categories.
    results = collection.aggregate([
        {"$match": {**_filter(statement_id), "status": "successful", "transaction_type": {"$in": ["payment", "expense"]}}},
        {"$group": {"_id": "$category", "total_amount": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        {"$sort": {"total_amount": -1}},
    ])
    return [{"category": r["_id"], "total_amount": r["total_amount"], "count": r["count"]} for r in results]


def get_summary_by_date(statement_id: str | None = None) -> list[dict]:
    # Spending trend uses only money that actually left the account.
    results = collection.aggregate([
        {"$match": {**_filter(statement_id), "status": "successful", "transaction_type": {"$in": ["payment", "expense"]}}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "total_amount": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ])
    return [{"date": r["_id"], "total_amount": r["total_amount"], "count": r["count"]} for r in results]
