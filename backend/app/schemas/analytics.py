from typing import List

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    """High-level overview combining several headline metrics in one response."""
    total_transactions: int
    # Money that actually left the account (successful payment/expense
    # transactions only) -- this is what the dashboard's "Total Spent"
    # card displays.
    total_spent_amount: float
    # Sum of ALL successful transactions regardless of type (payment,
    # refund, expense, chargeback combined). Kept for backward
    # compatibility; total_spent_amount is the precise "money spent"
    # figure used by the UI.
    total_successful_amount: float
    total_failed_count: int
    total_refund_amount: float


class StatusCount(BaseModel):
    """Number of transactions for a single status value (e.g. 'successful')."""
    status: str
    count: int


class TypeCount(BaseModel):
    """Number of transactions for a single transaction_type value (e.g. 'payment')."""
    transaction_type: str
    count: int


class CategorySummary(BaseModel):
    """Total amount and transaction count for a single category (e.g. 'groceries')."""
    category: str
    total_amount: float
    count: int


class DateSummary(BaseModel):
    """Total amount and transaction count for a single calendar day."""
    date: str
    total_amount: float
    count: int


class ByStatusResponse(BaseModel):
    results: List[StatusCount]


class ByTypeResponse(BaseModel):
    results: List[TypeCount]


class ByCategoryResponse(BaseModel):
    results: List[CategorySummary]


class ByDateResponse(BaseModel):
    results: List[DateSummary]