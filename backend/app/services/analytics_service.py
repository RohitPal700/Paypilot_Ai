from app.db.mongodb import db

# Reuses the existing MongoDB connection (app/db/mongodb.py) — no new
# MongoClient is created here. This is the SAME "transactions" collection
# used by transaction_service.py, just accessed independently so the
# analytics module stays decoupled from the transaction module.
collection = db["transactions"]


def get_summary() -> dict:
    """
    Compute the headline analytics numbers in a single pass:
    - total_transactions: count of ALL transactions, any status/type
    - total_successful_amount: sum of `amount` where status == "successful"
    - total_failed_count: count of transactions where status == "failed"
    - total_refund_amount: sum of `amount` where transaction_type == "refund"
    """
    total_transactions = collection.count_documents({})

    successful_amount_result = list(collection.aggregate([
        {"$match": {"status": "successful"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    total_successful_amount = (
        successful_amount_result[0]["total"] if successful_amount_result else 0.0
    )

    total_failed_count = collection.count_documents({"status": "failed"})

    refund_amount_result = list(collection.aggregate([
        {"$match": {"transaction_type": "refund"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    total_refund_amount = (
        refund_amount_result[0]["total"] if refund_amount_result else 0.0
    )

    return {
        "total_transactions": total_transactions,
        "total_successful_amount": total_successful_amount,
        "total_failed_count": total_failed_count,
        "total_refund_amount": total_refund_amount,
    }


def get_count_by_status() -> list[dict]:
    """
    Group transactions by their `status` field and count each group.
    Equivalent to: SELECT status, COUNT(*) FROM transactions GROUP BY status
    """
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    results = collection.aggregate(pipeline)
    return [{"status": r["_id"], "count": r["count"]} for r in results]


def get_count_by_type() -> list[dict]:
    """
    Group transactions by their `transaction_type` field and count each group.
    """
    pipeline = [
        {"$group": {"_id": "$transaction_type", "count": {"$sum": 1}}},
    ]
    results = collection.aggregate(pipeline)
    return [{"transaction_type": r["_id"], "count": r["count"]} for r in results]


def get_summary_by_category() -> list[dict]:
    """
    Group transactions by `category`, summing the amount and counting
    transactions in each category. Useful for a spending breakdown.
    """
    pipeline = [
        {"$group": {
            "_id": "$category",
            "total_amount": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
    ]
    results = collection.aggregate(pipeline)
    return [
        {"category": r["_id"], "total_amount": r["total_amount"], "count": r["count"]}
        for r in results
    ]


def get_summary_by_date() -> list[dict]:
    """
    Group transactions by the calendar day portion of `created_at`
    (which is stored as a real datetime), summing amount and counting
    transactions per day. Returned dates are formatted as "YYYY-MM-DD"
    and sorted chronologically.
    """
    pipeline = [
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "total_amount": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    results = collection.aggregate(pipeline)
    return [
        {"date": r["_id"], "total_amount": r["total_amount"], "count": r["count"]}
        for r in results
    ]