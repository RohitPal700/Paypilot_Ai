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