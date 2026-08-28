from enum import Enum

from pydantic import BaseModel, Field

# Reused, not redefined -- keeps the ML input's allowed transaction types
# identical to the ones the real transaction API accepts.
from app.schemas.transaction import TransactionType


class RiskTier(str, Enum):
    """Coarse-grained risk category derived from failure_probability."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PredictionRequest(BaseModel):
    """
    Prediction-time features for a transaction that hasn't happened yet
    (or whose outcome isn't known yet). Deliberately excludes status,
    customer_id, and created_at:
      - status is the thing we're predicting, not an input
      - customer_id carries no learned signal (see ML design review) and
        was excluded from training, so it's not accepted here either
      - created_at is not needed directly -- hour/day_of_week (its
        prediction-time-safe derived features) are supplied instead
    """
    merchant_id: str = Field(min_length=1, description="Merchant identifier")
    amount: float = Field(gt=0, description="Transaction amount, must be positive")
    currency: str = Field(min_length=3, max_length=3, description="3-letter currency code, e.g. USD")
    transaction_type: TransactionType
    payment_method: str = Field(min_length=1, description="e.g. upi, card, netbanking")
    category: str = Field(min_length=1, description="Transaction category")
    hour: int = Field(ge=0, le=23, description="Hour of day the transaction occurs, 0-23")
    day_of_week: int = Field(ge=0, le=6, description="Day of week, 0=Monday .. 6=Sunday")


class PredictionResponse(BaseModel):
    """Model output plus the business-policy risk tier derived from it."""
    failure_probability: float = Field(ge=0.0, le=1.0)
    risk_tier: RiskTier