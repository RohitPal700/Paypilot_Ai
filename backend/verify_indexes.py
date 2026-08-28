"""
Run this from backend/, with your real .env in place, to confirm the two
indexes exist against your actual MongoDB Atlas database:

    python verify_indexes.py

It does not create anything -- app/db/mongodb.py already creates the
indexes automatically on import (i.e. as soon as the app -- or this
script -- starts). This just lists what's actually on the collection
afterward, so you can see the real result for yourself.
"""

from app.db.mongodb import db

transactions = db["transactions"]

print("Indexes currently on the 'transactions' collection:\n")
for index in transactions.list_indexes():
    print(dict(index))

names = {index["name"] for index in transactions.list_indexes()}
print("\n--- Check ---")
print(f"uniq_transaction_id present: {'uniq_transaction_id' in names}")
print(f"idx_created_at present:      {'idx_created_at' in names}")