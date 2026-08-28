from fastapi import APIRouter, HTTPException

from app.ml.model_loader import ModelLoadError
from app.schemas.ml import PredictionRequest, PredictionResponse
from app.services.ml_service import predict_failure_risk

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.post("/predict-risk", response_model=PredictionResponse)
def predict_risk(payload: PredictionRequest):
    """
    Predict failure risk for a transaction that hasn't settled yet.

    Field validation (amount > 0, currency length, enum values, hour/
    day_of_week ranges, non-empty strings) is handled automatically by
    PredictionRequest before this function body runs -- FastAPI returns a
    422 with the validation details on its own for those cases.

    This is a decision-support signal, not an automated block/allow
    system, and the underlying model has known limitations (see the
    training/evaluation write-up) -- it is not being represented here as
    production-grade or as a guarantee of outcome.
    """
    try:
        return predict_failure_risk(payload)
    except ModelLoadError:
        # Model artifact missing/corrupt -- a real operational failure,
        # not a client mistake. 503 signals "try again later", and no
        # internal path or traceback is exposed.
        raise HTTPException(
            status_code=503,
            detail="Failure-risk prediction is temporarily unavailable.",
        )
    except Exception:
        # Catch-all so an unexpected internal error never surfaces a raw
        # traceback to the client. The real exception can still be
        # inspected server-side via logs/observability tooling.
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating the prediction.",
        )