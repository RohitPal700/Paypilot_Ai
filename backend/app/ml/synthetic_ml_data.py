"""
Synthetic dataset generator for the transaction-failure-risk ML problem.

This is deliberately SEPARATE from app/utils/synthetic_data.py, which exists
to power the API's /api/transactions/seed endpoint (demo/dev data only, with
an independently-random status field). That generator must not be used for
ML training, because its `status` field carries no relationship to any other
field -- there is nothing for a model to learn from it.

This module generates `status` as a function of the transaction's own
features (amount, payment_method, transaction_type, category, merchant_id,
time of day) plus random noise, via:

    score = weighted_sum(features) + noise
    p_failure = sigmoid(score)
    status = "failed" with probability p_failure,
             otherwise "successful" or "pending"

This keeps the relationship real (a model can learn it) but not perfectly
deterministic (a model can't just memorize a lookup table).

No FastAPI, no MongoDB, no other backend dependency -- this module can be
run and tested completely standalone.
"""

import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, TypedDict

from app.schemas.transaction import TransactionStatus, TransactionType

# ---------------------------------------------------------------------------
# Feature value pools
#
# Deliberately mirrors app/utils/synthetic_data.py's pools so the ML dataset
# and the live API's data look like they come from the same "world."
# ---------------------------------------------------------------------------

_MERCHANTS = [
    "merchant_bluewave", "merchant_urbancart", "merchant_freshbite",
    "merchant_techhive", "merchant_greenleaf", "merchant_swiftgear",
    "merchant_daily_grind_cafe", "merchant_pixel_studio",
]

_PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet", "bank_transfer"]

_CATEGORIES = [
    "groceries", "electronics", "software_subscription", "utilities",
    "travel", "food_delivery", "office_supplies", "marketing",
]

_CURRENCIES = ["USD", "INR", "EUR"]

_MAX_AMOUNT = 2500.0  # same range as the API's synthetic_data.py generator

# Same distribution as app/utils/synthetic_data.py, so the ML dataset's
# transaction_type mix matches what the live API produces.
_TRANSACTION_TYPE_DISTRIBUTION = {
    TransactionType.PAYMENT: 0.70,
    TransactionType.REFUND: 0.15,
    TransactionType.EXPENSE: 0.10,
    TransactionType.CHARGEBACK: 0.05,
}


def _weighted_choice(weights: dict):
    options = list(weights.keys())
    probabilities = list(weights.values())
    return random.choices(options, weights=probabilities, k=1)[0]

# Merchants we've designated as "riskier" for this synthetic world (e.g.
# smaller/newer merchants with less payment-gateway track record).
_RISKY_MERCHANTS = {"merchant_swiftgear", "merchant_pixel_studio"}

# ---------------------------------------------------------------------------
# Risk weights
#
# These are hand-chosen to encode plausible, explainable relationships (see
# the design discussion). They are intentionally moderate, not extreme --
# the goal is a learnable-but-noisy signal, not a deterministic rule.
# ---------------------------------------------------------------------------

_INTERCEPT = -3.35
# Calibrated (not just sigmoid(-2.44)=8%) to account for the fact that most
# feature weights are positive-or-zero, so the *average* transaction sits
# well above zero extra score even before noise. -3.35 was chosen empirically
# so the dataset-wide failure rate lands in the ~8-12% target range -- see
# generate_dataset.py's audit output for the actual observed rate.

_AMOUNT_WEIGHT = 1.5  # multiplied by (amount / _MAX_AMOUNT)

_PAYMENT_METHOD_WEIGHTS = {
    "upi": -0.3,
    "card": 0.0,
    "wallet": 0.1,
    "netbanking": 0.4,
    "bank_transfer": 0.6,
}

_TRANSACTION_TYPE_WEIGHTS = {
    TransactionType.PAYMENT: 0.0,
    TransactionType.EXPENSE: -0.2,
    TransactionType.REFUND: -0.1,
    TransactionType.CHARGEBACK: 0.5,
}

_CATEGORY_WEIGHTS = {
    "travel": 0.3,
    "electronics": 0.1,
    "groceries": -0.1,
    # all other categories default to 0.0 (see .get(..., 0.0) below)
}

_RISKY_MERCHANT_WEIGHT = 0.3
_LATE_NIGHT_WEIGHT = 0.3  # applied when the hour is in [0, 5]

_NOISE_STD_DEV = 0.5  # Gaussian noise added to the score before sigmoid

# After a transaction is *not* failed, split it between successful/pending
# in roughly this ratio (matches the API generator's ~80:12 successful:pending
# split, renormalized over the ~92% non-failed portion).
_PENDING_SHARE_OF_NON_FAILED = 0.13


class MLTransactionRow(TypedDict):
    merchant_id: str
    amount: float
    currency: str
    transaction_type: str
    payment_method: str
    customer_id: str
    category: str
    created_at: str  # ISO 8601
    hour: int
    day_of_week: int
    status: str


def sigmoid(x: float) -> float:
    """Squash any real number into the (0, 1) probability range."""
    return 1.0 / (1.0 + math.exp(-x))


def _random_created_at() -> datetime:
    """
    Random timestamp within the last 30 days, with the hour drawn uniformly
    across all 24 hours so late-night transactions are well represented.
    """
    days_ago = random.uniform(0, 30)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    base = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return base.replace(hour=hour, minute=minute, second=second, microsecond=0)


def compute_failure_probability(
    amount: float,
    payment_method: str,
    transaction_type: TransactionType,
    category: str,
    merchant_id: str,
    hour: int,
) -> float:
    """
    Combine feature weights into a score, add Gaussian noise, and convert
    to a probability via sigmoid.

    IMPORTANT: every input here must be something known BEFORE the
    transaction outcome is decided (i.e. no leakage) -- amount, method,
    type, category, merchant, and time of day are all set at transaction
    creation time, same as in the real API.
    """
    score = _INTERCEPT
    score += _AMOUNT_WEIGHT * (amount / _MAX_AMOUNT)
    score += _PAYMENT_METHOD_WEIGHTS.get(payment_method, 0.0)
    score += _TRANSACTION_TYPE_WEIGHTS.get(transaction_type, 0.0)
    score += _CATEGORY_WEIGHTS.get(category, 0.0)
    if merchant_id in _RISKY_MERCHANTS:
        score += _RISKY_MERCHANT_WEIGHT
    if 0 <= hour <= 5:
        score += _LATE_NIGHT_WEIGHT

    # Gaussian noise -- prevents the score from being a deterministic
    # function of the features alone, so the dataset isn't a lookup table.
    score += random.gauss(0.0, _NOISE_STD_DEV)

    return sigmoid(score)


def _sample_status(p_failure: float) -> TransactionStatus:
    """
    Sample the final status:
      - FAILED with probability p_failure
      - otherwise SUCCESSFUL or PENDING, split by _PENDING_SHARE_OF_NON_FAILED
    """
    if random.random() < p_failure:
        return TransactionStatus.FAILED
    if random.random() < _PENDING_SHARE_OF_NON_FAILED:
        return TransactionStatus.PENDING
    return TransactionStatus.SUCCESSFUL


def generate_ml_row() -> MLTransactionRow:
    """Generate a single synthetic transaction row with a causally-derived status."""
    merchant_id = random.choice(_MERCHANTS)
    amount = round(random.uniform(5.0, _MAX_AMOUNT), 2)
    currency = random.choice(_CURRENCIES)
    transaction_type = _weighted_choice(_TRANSACTION_TYPE_DISTRIBUTION)
    payment_method = random.choice(_PAYMENT_METHODS)
    category = random.choice(_CATEGORIES)
    created_at = _random_created_at()

    p_failure = compute_failure_probability(
        amount=amount,
        payment_method=payment_method,
        transaction_type=transaction_type,
        category=category,
        merchant_id=merchant_id,
        hour=created_at.hour,
    )
    status = _sample_status(p_failure)

    return {
        "merchant_id": merchant_id,
        "amount": amount,
        "currency": currency,
        "transaction_type": transaction_type.value,
        "payment_method": payment_method,
        "customer_id": f"customer_{random.randint(1000, 9999)}",
        "category": category,
        "created_at": created_at.isoformat(),
        "hour": created_at.hour,
        "day_of_week": created_at.weekday(),
        "status": status.value,
    }


def generate_ml_dataset(n: int) -> List[MLTransactionRow]:
    """Generate `n` synthetic rows for ML training."""
    return [generate_ml_row() for _ in range(n)]