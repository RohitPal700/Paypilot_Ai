"""
Pytest collects this file before any test module, so setting environment
variables here guarantees app.db.mongodb (which reads them at import time)
never touches a real database during the test suite -- regardless of
whether a real backend/.env is present locally.

A short serverSelectionTimeoutMS keeps the (expected, harmless) index
creation attempt in app/db/mongodb.py's startup code fast -- it fails in
well under a second instead of MongoDB's default 30s server-selection
timeout, so the test suite doesn't hang on every run.
"""

import os

os.environ["MONGODB_URI"] = "mongodb://localhost:27017/?serverSelectionTimeoutMS=200"
os.environ["MONGODB_DB_NAME"] = "paypilot_ai_test"