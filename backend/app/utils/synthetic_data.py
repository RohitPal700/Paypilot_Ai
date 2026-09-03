import random
from typing import List

from app.schemas.transaction import (
    Transaction,
    TransactionSource,
    TransactionStatus,
    TransactionType,
)

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

# Rough probability weights so most transactions are successful payments,
# similar to what a real merchant's transaction log tends to look like.
_TYPE_WEIGHTS = {
    TransactionType.PAYMENT: 0.70,
    TransactionType.REFUND: 0.15,
    TransactionType.EXPENSE: 0.10,
    TransactionType.CHARGEBACK: 0.05,
}

_STATUS_WEIGHTS = {
    TransactionStatus.SUCCESSFUL: 0.80,
    TransactionStatus.PENDING: 0.12,
    TransactionStatus.FAILED: 0.08,
}


def _weighted_choice(weights: dict):
    options = list(weights.keys())
    probabilities = list(weights.values())
    return random.choices(options, weights=probabilities, k=1)[0]


def generate_synthetic_transactions(count: int = 50) -> List[Transaction]:
    """Generate a list of realistic-looking synthetic transactions for testing."""
    transactions = []
    for i in range(count):
        transaction = Transaction(
            merchant_id=random.choice(_MERCHANTS),
            amount=round(random.uniform(5.0, 2500.0), 2),
            currency=random.choice(_CURRENCIES),
            transaction_type=_weighted_choice(_TYPE_WEIGHTS),
            status=_weighted_choice(_STATUS_WEIGHTS),
            payment_method=random.choice(_PAYMENT_METHODS),
            customer_id=f"customer_{random.randint(1000, 9999)}",
            category=random.choice(_CATEGORIES),
            # Tagged explicitly so the analytics layer can exclude this
            # demo/test data from the user-facing dashboard -- see
            # TransactionSource in app/schemas/transaction.py.
            source=TransactionSource.SYNTHETIC_SEED,
        )
        transactions.append(transaction)
    return transactions 