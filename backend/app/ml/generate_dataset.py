"""
Generate the ML training dataset and audit it for learnable signal.

Usage (from the backend/ directory, so the `app` package resolves):

    python -m app.ml.generate_dataset

This is a standalone script -- no MongoDB, no FastAPI, no .env required.
It writes data/ml_training_dataset.csv (relative to the repo root) and
prints statistics confirming the injected feature -> failure relationship
is actually present in the generated data (not just assumed).
"""

import csv
import os
from collections import Counter, defaultdict

from app.ml.synthetic_ml_data import generate_ml_dataset

N_ROWS = 4000

# backend/app/ml/generate_dataset.py -> repo root is three levels up
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
_OUTPUT_PATH = os.path.join(_REPO_ROOT, "data", "ml_training_dataset.csv")

_CSV_COLUMNS = [
    "merchant_id", "amount", "currency", "transaction_type",
    "payment_method", "customer_id", "category", "created_at",
    "hour", "day_of_week", "status",
]

_AMOUNT_BUCKETS = [
    ("0-500", 0, 500),
    ("500-1000", 500, 1000),
    ("1000-1500", 1000, 1500),
    ("1500-2000", 1500, 2000),
    ("2000-2500", 2000, 2500),
]


def _write_csv(rows, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _amount_bucket(amount: float) -> str:
    for label, lo, hi in _AMOUNT_BUCKETS:
        if lo <= amount < hi:
            return label
    return _AMOUNT_BUCKETS[-1][0]


def _print_audit(rows) -> None:
    total = len(rows)
    status_counts = Counter(r["status"] for r in rows)
    failed = status_counts.get("failed", 0)
    successful = status_counts.get("successful", 0)
    pending = status_counts.get("pending", 0)

    print("=" * 60)
    print("ML TRAINING DATASET AUDIT")
    print("=" * 60)
    print(f"Total rows generated: {total}")
    print()
    print("Status breakdown:")
    print(f"  successful : {successful:5d}  ({successful/total:.1%})")
    print(f"  failed     : {failed:5d}  ({failed/total:.1%})")
    print(f"  pending    : {pending:5d}  ({pending/total:.1%})")
    print()
    print(f"Overall failure rate (failed / total): {failed/total:.2%}")
    print()

    # --- Failure rate by payment_method ---
    print("Failure rate by payment_method:")
    by_method_total = Counter(r["payment_method"] for r in rows)
    by_method_failed = Counter(
        r["payment_method"] for r in rows if r["status"] == "failed"
    )
    for method in sorted(by_method_total, key=lambda m: -by_method_failed[m] / by_method_total[m]):
        t = by_method_total[method]
        f = by_method_failed[method]
        print(f"  {method:15s}: {f:4d} / {t:4d}  = {f/t:.2%}")
    print()

    # --- Failure rate by amount bucket ---
    print("Failure rate by amount bucket:")
    by_bucket_total = defaultdict(int)
    by_bucket_failed = defaultdict(int)
    for r in rows:
        bucket = _amount_bucket(r["amount"])
        by_bucket_total[bucket] += 1
        if r["status"] == "failed":
            by_bucket_failed[bucket] += 1
    for label, _, _ in _AMOUNT_BUCKETS:
        t = by_bucket_total[label]
        f = by_bucket_failed[label]
        rate = f / t if t else 0.0
        print(f"  {label:12s}: {f:4d} / {t:4d}  = {rate:.2%}")
    print()

    # --- Failure rate by category ---
    print("Failure rate by category:")
    by_cat_total = Counter(r["category"] for r in rows)
    by_cat_failed = Counter(r["category"] for r in rows if r["status"] == "failed")
    for cat in sorted(by_cat_total, key=lambda c: -by_cat_failed[c] / by_cat_total[c]):
        t = by_cat_total[cat]
        f = by_cat_failed[cat]
        print(f"  {cat:22s}: {f:4d} / {t:4d}  = {f/t:.2%}")
    print()

    # --- Failure rate: risky vs non-risky merchants ---
    from app.ml.synthetic_ml_data import _RISKY_MERCHANTS  # audit-only import

    risky_rows = [r for r in rows if r["merchant_id"] in _RISKY_MERCHANTS]
    other_rows = [r for r in rows if r["merchant_id"] not in _RISKY_MERCHANTS]
    risky_failed = sum(1 for r in risky_rows if r["status"] == "failed")
    other_failed = sum(1 for r in other_rows if r["status"] == "failed")
    print("Failure rate: risky merchants vs. others:")
    print(f"  risky merchants  : {risky_failed:4d} / {len(risky_rows):4d} = {risky_failed/len(risky_rows):.2%}")
    print(f"  other merchants  : {other_failed:4d} / {len(other_rows):4d} = {other_failed/len(other_rows):.2%}")
    print()

    # --- Failure rate: late night (0-5h) vs rest of day ---
    late_rows = [r for r in rows if 0 <= r["hour"] <= 5]
    rest_rows = [r for r in rows if not (0 <= r["hour"] <= 5)]
    late_failed = sum(1 for r in late_rows if r["status"] == "failed")
    rest_failed = sum(1 for r in rest_rows if r["status"] == "failed")
    print("Failure rate: late night (00-05h) vs rest of day:")
    print(f"  late night (00-05h): {late_failed:4d} / {len(late_rows):4d} = {late_failed/len(late_rows):.2%}")
    print(f"  rest of day        : {rest_failed:4d} / {len(rest_rows):4d} = {rest_failed/len(rest_rows):.2%}")
    print("=" * 60)


def main() -> None:
    rows = generate_ml_dataset(N_ROWS)
    _write_csv(rows, _OUTPUT_PATH)
    print(f"Wrote {len(rows)} rows to {_OUTPUT_PATH}")
    print()
    _print_audit(rows)


if __name__ == "__main__":
    main()