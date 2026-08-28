"""
Service layer for the failure-risk prediction endpoint.

Takes an already-validated PredictionRequest, builds the single-row feature
table the saved Pipeline expects (same column names as training -- see
app/ml/train.py FEATURE_COLUMNS), and passes it straight to the pipeline.
No manual encoding or scaling happens here: the saved Pipeline already
contains the fitted OneHotEncoder and StandardScaler from training, so raw
feature values go in and a probability comes out.
"""

import pandas as pd

from app.ml.model_loader import get_model
from app.ml.risk_policy import probability_to_risk_tier
from app.schemas.ml import PredictionRequest, PredictionResponse


def predict_failure_risk(payload: PredictionRequest) -> PredictionResponse:
    pipeline = get_model()  # cached after the first call, not reloaded here

    # Column names must match what the pipeline's ColumnTransformer was
    # fit on (NUMERIC_FEATURES + CATEGORICAL_FEATURES in app/ml/train.py).
    # .value on the enum converts it to the plain string ("payment", etc.)
    # the encoder was actually trained on.
    row = pd.DataFrame([{
        "amount": payload.amount,
        "hour": payload.hour,
        "day_of_week": payload.day_of_week,
        "currency": payload.currency,
        "transaction_type": payload.transaction_type.value,
        "payment_method": payload.payment_method,
        "category": payload.category,
        "merchant_id": payload.merchant_id,
    }])

    probability = float(pipeline.predict_proba(row)[0, 1])
    tier = probability_to_risk_tier(probability)

    return PredictionResponse(failure_probability=probability, risk_tier=tier)