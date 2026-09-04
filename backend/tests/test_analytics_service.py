"""
Unit tests for app/services/analytics_service.py itself (not just the API
routing layer -- see test_analytics.py for that).

These verify the specific, critical behavior for demo/real data
separation: every query the dashboard depends on must operate ONLY on
transactions tagged source == "statement_import" (i.e. rows that came
from an uploaded statement). This is deliberately narrower than "not
synthetic_seed" -- it also excludes manually-created test transactions
and legacy documents with no source field at all, since neither of those
represents an uploaded statement.

No real MongoDB is used. `collection` is replaced with a lightweight fake
that just records what filter/pipeline it was called with, following the
same monkeypatch-based approach as the rest of this test suite.
"""

import app.services.analytics_service as analytics_service


class FakeCollection:
    """Records every call made to it; returns empty/zero results."""

    def __init__(self):
        self.count_documents_calls = []
        self.aggregate_calls = []

    def count_documents(self, filter_):
        self.count_documents_calls.append(filter_)
        return 0

    def aggregate(self, pipeline):
        self.aggregate_calls.append(pipeline)
        return []


def _install_fake_collection(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(analytics_service, "collection", fake)
    return fake


def _pipeline_is_statement_import_only(pipeline) -> bool:
    """True if the pipeline's first $match stage restricts to statement_import."""
    for stage in pipeline:
        match_stage = stage.get("$match")
        if match_stage and match_stage.get("source") == "statement_import":
            return True
    return False


def test_real_data_filter_is_statement_import_only():
    """
    Guards the exact filter shape. Deliberately NOT `{"$ne": "synthetic_seed"}`
    -- that's too broad and would let manual/legacy no-source documents
    leak into the dashboard again.
    """
    assert analytics_service.REAL_DATA_FILTER == {"source": "statement_import"}


def test_get_summary_only_reads_statement_import_data(monkeypatch):
    fake = _install_fake_collection(monkeypatch)

    analytics_service.get_summary()

    # count_documents is called twice (total_transactions, total_failed_count)
    assert len(fake.count_documents_calls) == 2
    for filter_ in fake.count_documents_calls:
        assert filter_.get("source") == "statement_import"

    # aggregate is called three times (successful, spent, refund amounts)
    assert len(fake.aggregate_calls) == 3
    for pipeline in fake.aggregate_calls:
        assert _pipeline_is_statement_import_only(pipeline)


def test_get_summary_separates_spent_from_all_successful_amount(monkeypatch):
    """
    total_spent_amount must only include payment/expense transaction
    types -- not refunds -- unlike total_successful_amount which sums
    every successful transaction regardless of type.
    """
    fake = _install_fake_collection(monkeypatch)

    analytics_service.get_summary()

    spent_pipeline = fake.aggregate_calls[1]
    match_stage = spent_pipeline[0]["$match"]
    assert match_stage["transaction_type"] == {"$in": ["payment", "expense"]}
    assert match_stage["status"] == "successful"
    assert match_stage["source"] == "statement_import"


def test_get_summary_refund_amount_requires_successful_status(monkeypatch):
    """A pending/failed refund hasn't actually been received back yet."""
    fake = _install_fake_collection(monkeypatch)

    analytics_service.get_summary()

    refund_pipeline = fake.aggregate_calls[2]
    match_stage = refund_pipeline[0]["$match"]
    assert match_stage["transaction_type"] == "refund"
    assert match_stage["status"] == "successful"
    assert match_stage["source"] == "statement_import"


def test_get_count_by_status_only_reads_statement_import_data(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    analytics_service.get_count_by_status()
    assert _pipeline_is_statement_import_only(fake.aggregate_calls[0])


def test_get_count_by_type_only_reads_statement_import_data(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    analytics_service.get_count_by_type()
    assert _pipeline_is_statement_import_only(fake.aggregate_calls[0])


def test_get_summary_by_category_only_reads_statement_import_data(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    analytics_service.get_summary_by_category()
    assert _pipeline_is_statement_import_only(fake.aggregate_calls[0])


def test_get_summary_by_date_only_reads_statement_import_data(monkeypatch):
    fake = _install_fake_collection(monkeypatch)
    analytics_service.get_summary_by_date()
    assert _pipeline_is_statement_import_only(fake.aggregate_calls[0])


def test_manual_and_legacy_no_source_documents_are_excluded(monkeypatch):
    """
    Regression test for the exact bug reported: manually-created test
    transactions (source == "manual") and legacy documents with no
    "source" field at all must NOT be included, even though they are
    real (non-synthetic) documents. Only source == "statement_import"
    counts as the active statement's data.
    """
    fake = _install_fake_collection(monkeypatch)

    analytics_service.get_summary_by_category()

    match_stage = fake.aggregate_calls[0][0]["$match"]
    # An exact-match filter on "statement_import" naturally excludes any
    # other value (including a missing field, "manual", or
    # "synthetic_seed") -- assert the filter is exact-match, not $ne.
    assert match_stage["source"] == "statement_import"
    assert match_stage["status"] == "successful"
    assert match_stage["transaction_type"] == {"$in": ["payment", "expense"]}