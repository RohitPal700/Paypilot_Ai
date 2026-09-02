"""
Decision-threshold analysis for the failure-risk model.

Usage (from the backend/ directory):

    python -m app.ml.threshold_analysis

This loads the already-trained pipeline (app/ml/artifacts/failure_risk_model.joblib,
produced by app/ml/train.py) and the same held-out test split used during
training, then reports precision/recall/F1 across a range of probability
thresholds -- rather than only at the default 0.5 cutoff.

WHY THIS EXISTS:
A classifier's predict_proba() output is a probability; predict() just
applies a 0.5 threshold to it by default. For an imbalanced problem like
this one (failures are ~12% of transactions), 0.5 is an arbitrary choice --
there's no reason the "right" cutoff for flagging a transaction as risky
happens to be exactly 0.5. This script exists to make that choice
deliberate and visible instead of silently accepting sklearn's default.

RELATIONSHIP TO risk_policy.py:
This script informs, but does not automatically set, the LOW_THRESHOLD /
HIGH_THRESHOLD constants in app/ml/risk_policy.py. Those tier boundaries
are a business-policy decision (how many false alarms is a "flag for
review" workflow willing to tolerate, in exchange for catching more real
failures?) that depends on a cost trade-off this script cannot know on its
own. What this script CAN show is the actual precision/recall trade-off at
each candidate threshold, so that policy decision is made with real numbers
instead of a guess.

Uses the SAME train/test split as train.py (same CSV, same filtering, same
random_state=42) so the reported numbers are directly comparable -- this
is evaluation on genuinely held-out data, not the training set.
"""

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.ml.model_loader import get_model
from app.ml.train import (
    FEATURE_COLUMNS,
    POSITIVE_LABEL,
    RANDOM_STATE,
    TARGET_COLUMN,
    TEST_SIZE,
    load_training_frame,
)

# Candidate thresholds to evaluate, from lenient (flags almost everything)
# to strict (flags almost nothing).
_THRESHOLDS = np.round(np.arange(0.05, 0.95, 0.05), 2)


def main() -> None:
    df = load_training_frame()
    y = (df[TARGET_COLUMN] == POSITIVE_LABEL).astype(int)
    X = df[FEATURE_COLUMNS]

    # Identical split call to train.py -- reproduces the exact same test
    # set without needing to persist it separately, as long as the input
    # CSV and filtering logic haven't changed since the model was trained.
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )

    pipeline = get_model()
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    print("=" * 72)
    print("THRESHOLD ANALYSIS (test set, n =", len(y_test), ", positives =", int(y_test.sum()), ")")
    print("=" * 72)
    print(f"{'Threshold':>10} {'Flagged':>9} {'Precision':>10} {'Recall':>8} {'F1':>8}")

    for threshold in _THRESHOLDS:
        y_pred = (y_proba >= threshold).astype(int)
        flagged = int(y_pred.sum())
        precision = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
        recall = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
        f1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
        print(f"{threshold:>10.2f} {flagged:>9d} {precision:>10.3f} {recall:>8.3f} {f1:>8.3f}")

    print()
    print("-" * 72)
    print("READING THIS TABLE:")
    print("  - Lower thresholds flag more transactions -> higher recall, lower precision.")
    print("  - Higher thresholds flag fewer transactions -> higher precision, lower recall.")
    print("  - There is no single 'correct' threshold here: the right choice depends on")
    print("    the relative cost of a missed failure (false negative) vs. an unnecessary")
    print("    manual review (false positive), which is a business decision, not a")
    print("    statistical one. See app/ml/risk_policy.py for the MVP policy chosen.")
    print("-" * 72)


if __name__ == "__main__":
    main()