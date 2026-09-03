from app.db.mongodb import db

# Reuses the existing MongoDB connection (app/db/mongodb.py) — no new
# MongoClient is created here. This is the SAME "transactions" collection
# used by transaction_service.py, just accessed independently so the
# analytics module stays decoupled from the transaction module.
collection = db["transactions"]

# Every analytics query in this module operates ONLY on transactions
# imported from a real uploaded statement (see TransactionSource in
# app/schemas/transaction.py). This is deliberately narrow -- NOT just
# "not synthetic_seed" -- because the dashboard's financial report must
# represent an uploaded statement specifically, not any other kind of
# data sitting in the collection.
#
# In particular this also excludes:
#   - "manual" transactions (created via POST /api/transactions, e.g.
#     through Swagger during development/testing -- these are not part
#     of any statement the user uploaded)
#   - legacy documents with no "source" field at all (pre-dating this
#     field; historically these came from manual testing/seeding, not
#     from a real statement, so they must NOT be silently included just
#     because they're "backward compatible")
#
# Demo/test data is NOT deleted anywhere -- it simply isn't part of the
# dataset these queries read. It remains available for local development
# and ML testing exactly as before.
REAL_DATA_FILTER = {"source": "statement_import"}


def get_summary() -> dict:
    """
    Compute the headline analytics numbers in a single pass, over the
    active uploaded statement's transactions only:
    - total_transactions: count of all real transactions, any status/type
    - total_spent_amount: sum of `amount` where status == "successful" AND
      transaction_type is "payment" or "expense" (i.e. money that actually
      left the account) -- this is what "Total Spent" on the dashboard
      means, and deliberately excludes refunds/chargebacks so it isn't
      inflated or deflated by money moving the other direction.
    - total_successful_amount: sum of `amount` where status == "successful",
      across ALL transaction types. Kept for backward compatibility with
      existing consumers of this field; total_spent_amount is the more
      precise "money spent" figure and is what the dashboard now displays.
    - total_failed_count: count of transactions where status == "failed"
    - total_refund_amount: sum of `amount` where transaction_type ==
      "refund" AND status == "successful" (a pending/failed refund hasn't
      actually been received back yet, so it shouldn't count).
    """
    base_match = REAL_DATA_FILTER
    total_transactions = collection.count_documents(base_match)

    successful_amount_result = list(collection.aggregate([
        {"$match": {**base_match, "status": "successful"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    total_successful_amount = (
        successful_amount_result[0]["total"] if successful_amount_result else 0.0
    )

    spent_amount_result = list(collection.aggregate([
        {"$match": {
            **base_match,
            "status": "successful",
            "transaction_type": {"$in": ["payment", "expense"]},
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    total_spent_amount = (
        spent_amount_result[0]["total"] if spent_amount_result else 0.0
    )

    total_failed_count = collection.count_documents({**base_match, "status": "failed"})

    refund_amount_result = list(collection.aggregate([
        {"$match": {**base_match, "transaction_type": "refund", "status": "successful"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    total_refund_amount = (
        refund_amount_result[0]["total"] if refund_amount_result else 0.0
    )

    return {
        "total_transactions": total_transactions,
        "total_spent_amount": total_spent_amount,
        "total_successful_amount": total_successful_amount,
        "total_failed_count": total_failed_count,
        "total_refund_amount": total_refund_amount,
    }


def get_count_by_status() -> list[dict]:
    """
    Group the active statement's transactions by their `status` field and count
    each group. Equivalent to:
    SELECT status, COUNT(*) FROM transactions WHERE <real> GROUP BY status
    """
    pipeline = [
        {"$match": REAL_DATA_FILTER},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    results = collection.aggregate(pipeline)
    return [{"status": r["_id"], "count": r["count"]} for r in results]


def get_count_by_type() -> list[dict]:
    """
    Group the active statement's transactions by their `transaction_type` field
    and count each group.
    """
    pipeline = [
        {"$match": REAL_DATA_FILTER},
        {"$group": {"_id": "$transaction_type", "count": {"$sum": 1}}},
    ]
    results = collection.aggregate(pipeline)
    return [{"transaction_type": r["_id"], "count": r["count"]} for r in results]


def get_summary_by_category() -> list[dict]:
    """
    Group the active statement's transactions by `category`, summing the amount
    and counting transactions in each category. Powers the "Where Your
    Money Went" breakdown.
    """
    pipeline = [
        {"$match": REAL_DATA_FILTER},
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
    Group the active statement's transactions by the calendar day portion of
    `created_at` (which is stored as a real datetime -- for statement
    imports, this is the actual date parsed from the PDF, not the upload
    date), summing amount and counting transactions per day. Returned
    dates are formatted as "YYYY-MM-DD" and sorted chronologically. Powers
    the Spending Trend chart.
    """
    pipeline = [
        {"$match": REAL_DATA_FILTER},
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