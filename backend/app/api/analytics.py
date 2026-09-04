from fastapi import APIRouter, Query

from app.schemas.analytics import AnalyticsSummary, ByCategoryResponse, ByDateResponse, ByStatusResponse, ByTypeResponse
from app.services.analytics_service import get_count_by_status, get_count_by_type, get_summary, get_summary_by_category, get_summary_by_date

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _call(fn, statement_id):
    return fn() if statement_id is None else fn(statement_id)


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(statement_id: str | None = Query(default=None)):
    return _call(get_summary, statement_id)


@router.get("/by-status", response_model=ByStatusResponse)
def analytics_by_status(statement_id: str | None = Query(default=None)):
    return {"results": _call(get_count_by_status, statement_id)}


@router.get("/by-type", response_model=ByTypeResponse)
def analytics_by_type(statement_id: str | None = Query(default=None)):
    return {"results": _call(get_count_by_type, statement_id)}


@router.get("/by-category", response_model=ByCategoryResponse)
def analytics_by_category(statement_id: str | None = Query(default=None)):
    return {"results": _call(get_summary_by_category, statement_id)}


@router.get("/by-date", response_model=ByDateResponse)
def analytics_by_date(statement_id: str | None = Query(default=None)):
    return {"results": _call(get_summary_by_date, statement_id)}
