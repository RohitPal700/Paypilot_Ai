from fastapi import APIRouter

from app.schemas.analytics import (
    AnalyticsSummary,
    ByCategoryResponse,
    ByDateResponse,
    ByStatusResponse,
    ByTypeResponse,
)
from app.services.analytics_service import (
    get_count_by_status,
    get_count_by_type,
    get_summary,
    get_summary_by_category,
    get_summary_by_date,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary():
    """
    Headline numbers: total transaction count, total successful amount,
    total failed count, and total refund amount.
    """
    return get_summary()


@router.get("/by-status", response_model=ByStatusResponse)
def analytics_by_status():
    """Transaction count grouped by status (successful/failed/pending)."""
    return {"results": get_count_by_status()}


@router.get("/by-type", response_model=ByTypeResponse)
def analytics_by_type():
    """Transaction count grouped by transaction_type (payment/refund/chargeback/expense)."""
    return {"results": get_count_by_type()}


@router.get("/by-category", response_model=ByCategoryResponse)
def analytics_by_category():
    """Total amount and transaction count grouped by category."""
    return {"results": get_summary_by_category()}


@router.get("/by-date", response_model=ByDateResponse)
def analytics_by_date():
    """Total amount and transaction count grouped by calendar day (created_at)."""
    return {"results": get_summary_by_date()}