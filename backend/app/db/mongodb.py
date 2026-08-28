import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Load variables from backend/.env into the environment.
# This must run before we read os.getenv() below.
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "paypilot_ai")

if not MONGODB_URI:
    raise ValueError(
        "MONGODB_URI is not set. Please add it to backend/.env "
        "(see backend/.env.example)."
    )

# Create a single, reusable MongoDB client.
# PyMongo's client manages its own connection pool internally,
# so this same `client` (and `db`) can be imported anywhere in the
# backend without creating a new connection each time.
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB_NAME]


def create_indexes() -> None:
    """
    Ensure the indexes required by the transaction/analytics query patterns
    exist on the transactions collection.

    - transaction_id: unique index. Lookups by transaction_id
      (get_transaction_by_id) currently do a full collection scan; this
      also gives us a hard database-level guarantee against duplicate IDs,
      since transaction_id is meant to identify exactly one transaction.
    - created_at: regular (non-unique) index. Analytics' by-date grouping
      and sorting ($group/$sort on created_at) currently scans and sorts
      every document in memory; an index lets MongoDB use its pre-sorted
      structure instead.

    create_index() is idempotent: calling it again with the same field and
    options on every app startup is a safe no-op if the index already
    exists. It only raises if an index with the same NAME already exists
    with a DIFFERENT definition, which isn't the case here.
    """
    transactions = db["transactions"]
    transactions.create_index("transaction_id", unique=True, name="uniq_transaction_id")
    transactions.create_index("created_at", name="idx_created_at")


# Run index creation once, at import time -- i.e. whenever the application
# starts (mirrors how `client`/`db` above are already set up at import
# time). Failures here don't crash the app; DB availability is already
# separately surfaced via check_connection()/`GET /health/db`.
try:
    create_indexes()
except PyMongoError as exc:
    print(f"Warning: could not create MongoDB indexes at startup: {exc}")


def check_connection() -> bool:
    """
    Verify that MongoDB is reachable using a lightweight 'ping' command.
    Returns True if the ping succeeds, False otherwise.
    Never raises the connection details (URI/password) to the caller.
    """
    try:
        client.admin.command("ping")
        return True
    except PyMongoError:
        return False