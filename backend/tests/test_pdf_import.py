"""
Tests for the PDF statement import feature: POST /api/import/pdf and the
underlying app/services/pdf_import_service.py parsing logic.

Two layers of testing, consistent with the rest of this test suite:

1. Parser unit tests (parse_statement_text, build_transaction,
   deterministic ID generation) -- pure functions, no MongoDB, no HTTP.
2. API-level tests (routing, content-type/validation, response shape) --
   using FastAPI's TestClient with the actual import_pdf service function
   monkeypatched, following the same pattern as test_transactions.py and
   test_analytics.py, so no real database connection is required.

A synthetic statement PDF is generated in-memory with fpdf2 for the
fixture used below -- fpdf2 is a test-only dependency (see requirements.txt),
not something the running application depends on.

HONESTY NOTE: these tests do not exercise a real MongoDB Atlas connection
(none is available in this environment). "Imported transactions reach the
analytics layer" is verified here at the architecture level (same
collection object, same database connection) plus via the parser producing
valid Transaction records with real dates -- not via a live end-to-end
database round-trip. See the accompanying report for what this does and
does not prove.
"""

from datetime import datetime, timezone

import app.api.import_pdf as import_pdf_api
from fastapi.testclient import TestClient
from fpdf import FPDF

from app.main import app
from app.schemas.import_result import ImportResult
from app.services.pdf_import_service import (
    build_transaction,
    parse_statement_text,
)

client = TestClient(app)
ENDPOINT = "/api/import/pdf"


def _build_sample_statement_pdf() -> bytes:
    """
    Generates a small, realistic-looking PhonePe-style statement PDF
    in-memory (never written to disk) with 5 known transaction rows,
    spanning multiple dates -- this is what lets the Spending Trend
    analytics show a real multi-point chart once imported.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    lines = [
        "PhonePe Transaction Statement",
        "Statement Period: 01 Jul 2025 - 31 Jul 2025",
        "",
        "03 Jul 2025 Paid to Amazon Seller Services Debit Rs.1,499.00",
        "05 Jul 2025 Paid to Swiggy Bangalore Debit Rs.342.50",
        "08 Jul 2025 Received from Rohan Mehta Credit Rs.500.00",
        "12 Jul 2025 Paid to Uber India Debit Rs.215.00",
        "15 Jul 2025 Paid to Electricity Board Debit Rs.1,200.00",
    ]
    for line in lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


# --- Parser unit tests (no HTTP, no MongoDB) ----------------------------


def test_parse_statement_text_extracts_all_known_rows():
    text = (
        "03 Jul 2025 Paid to Amazon Seller Services Debit Rs.1,499.00\n"
        "05 Jul 2025 Paid to Swiggy Bangalore Debit Rs.342.50\n"
        "08 Jul 2025 Received from Rohan Mehta Credit Rs.500.00\n"
    )
    rows, failed, warnings = parse_statement_text(text)

    assert len(rows) == 3
    assert failed == 0
    assert warnings == []
    assert rows[0].amount == 1499.00
    assert rows[0].currency == "INR"
    assert rows[0].date.year == 2025 and rows[0].date.month == 7 and rows[0].date.day == 3


def test_parse_statement_text_ignores_headers_and_non_transaction_lines():
    text = (
        "PhonePe Transaction Statement\n"
        "Statement Period: 01 Jul 2025 - 31 Jul 2025\n"
        "Total Debited: Rs.3,256.50\n"
        "\n"
        "   \n"
    )
    rows, failed, warnings = parse_statement_text(text)

    # None of these lines have BOTH a date and an amount, so none should
    # be misclassified as transactions or counted as failures.
    assert rows == []
    assert failed == 0
    assert "No transaction rows were found" in warnings[0]


def test_parse_statement_text_handles_empty_input_gracefully():
    rows, failed, warnings = parse_statement_text("")
    assert rows == []
    assert failed == 0
    assert len(warnings) == 1


def test_parse_statement_text_infers_debit_as_payment_and_credit_as_refund():
    text = (
        "03 Jul 2025 Paid to Amazon Debit Rs.100.00\n"
        "08 Jul 2025 Received from Friend Credit Rs.50.00\n"
    )
    rows, _, _ = parse_statement_text(text)

    assert rows[0].transaction_type.value == "payment"
    assert rows[1].transaction_type.value == "refund"


def test_build_transaction_uses_real_parsed_date_not_current_time():
    text = "03 Jul 2025 Paid to Amazon Debit Rs.100.00"
    rows, _, _ = parse_statement_text(text)
    transaction = build_transaction(rows[0])

    assert transaction.created_at.year == 2025
    assert transaction.created_at.month == 7
    assert transaction.created_at.day == 3
    # Sanity check it's genuinely NOT "now" -- would only coincidentally
    # match if this test happened to run on 3 Jul 2025.
    assert transaction.created_at.date() != datetime.now(timezone.utc).date()


def test_deterministic_transaction_id_is_stable_across_parses():
    """
    Same PDF text parsed twice must produce identical transaction_ids --
    this is what allows re-uploading the same statement to be safely
    detected as duplicates via the existing unique index on transaction_id.
    """
    text = "03 Jul 2025 Paid to Amazon Debit Rs.100.00"

    rows_first, _, _ = parse_statement_text(text)
    rows_second, _, _ = parse_statement_text(text)

    id_first = build_transaction(rows_first[0]).transaction_id
    id_second = build_transaction(rows_second[0]).transaction_id

    assert id_first == id_second
    assert id_first.startswith("pdf_")


def test_deterministic_transaction_id_differs_for_different_rows():
    text = (
        "03 Jul 2025 Paid to Amazon Debit Rs.100.00\n"
        "05 Jul 2025 Paid to Swiggy Debit Rs.200.00\n"
    )
    rows, _, _ = parse_statement_text(text)
    ids = [build_transaction(r).transaction_id for r in rows]
    assert len(set(ids)) == len(ids)


def test_build_transaction_is_tagged_as_statement_import():
    """
    Every transaction built from a parsed PDF row must be tagged
    source="statement_import" so analytics_service can distinguish real
    statement data from synthetic seed/demo data.
    """
    text = "03 Jul 2025 Paid to Amazon Debit Rs.100.00"
    rows, _, _ = parse_statement_text(text)
    transaction = build_transaction(rows[0])
    assert transaction.source.value == "statement_import"


# --- Category classification (real PhonePe-style statement lines) ------


def test_infers_expected_categories_for_common_phonepe_merchants():
    text = (
        "01 Aug 2026 Paid to Meesho Debit Rs.850.00\n"
        "02 Aug 2026 Paid to RKGIT Canteen Debit Rs.120.00\n"
        "03 Aug 2026 Paid to Mobile Recharge Debit Rs.239.00\n"
        "04 Aug 2026 Paid to General Store Debit Rs.340.00\n"
        "05 Aug 2026 Paid to Pasta Grilled Debit Rs.180.00\n"
        "06 Aug 2026 Paid to Shadowfax Debit Rs.60.00\n"
    )
    rows, failed, _ = parse_statement_text(text)
    assert failed == 0
    categories = [r.category for r in rows]
    assert categories == [
        "Shopping",
        "Food",
        "Mobile Recharge",
        "Groceries",
        "Food",
        "Delivery",
    ]


def test_uncategorized_credit_with_no_merchant_keyword_is_a_transfer():
    text = "08 Jul 2025 Received from Rohan Mehta Credit Rs.500.00"
    rows, _, _ = parse_statement_text(text)
    assert rows[0].category == "Transfers"


# --- API-level tests (routing/validation; service layer monkeypatched) --


def test_upload_rejects_non_pdf_content_type():
    response = client.post(
        ENDPOINT,
        files={"file": ("statement.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_empty_file():
    response = client.post(
        ENDPOINT,
        files={"file": ("statement.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_rejects_content_that_is_not_actually_a_pdf():
    # Correct content_type header, but the bytes don't start with the PDF
    # magic number -- this is the "spoofed content-type" case.
    response = client.post(
        ENDPOINT,
        files={"file": ("statement.pdf", b"this is definitely not a pdf file", "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_success_returns_import_result_shape(monkeypatch):
    fake_result = ImportResult(
        imported=5, skipped_duplicates=0, failed_rows=0, warnings=[], errors=[]
    )
    monkeypatch.setattr(import_pdf_api, "import_pdf", lambda file_bytes: fake_result)

    pdf_bytes = _build_sample_statement_pdf()
    response = client.post(
        ENDPOINT,
        files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 5
    assert body["skipped_duplicates"] == 0
    assert body["failed_rows"] == 0


def test_upload_never_leaks_internal_error_details(monkeypatch):
    def boom(file_bytes):
        raise RuntimeError("some internal detail that should never reach the client")

    monkeypatch.setattr(import_pdf_api, "import_pdf", boom)

    pdf_bytes = _build_sample_statement_pdf()
    response = client.post(
        ENDPOINT,
        files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 500
    body = response.json()
    assert "internal detail" not in body["detail"]
    assert "RuntimeError" not in body["detail"]


# --- Architecture consistency: does this actually reach analytics? ------


def test_pdf_import_service_writes_to_the_same_collection_analytics_reads_from():
    """
    Doesn't touch a real database -- verifies at the object-identity level
    that pdf_import_service uses the exact same MongoDB connection and
    collection as transaction_service/analytics_service, so anything
    inserted here is automatically visible to the existing analytics
    endpoints with no additional wiring.
    """
    import app.db.mongodb as mongodb_module
    import app.services.analytics_service as analytics_service
    import app.services.pdf_import_service as pdf_import_service
    import app.services.transaction_service as transaction_service

    assert pdf_import_service.db is mongodb_module.db
    assert pdf_import_service.collection.name == "transactions"
    assert pdf_import_service.collection.name == transaction_service.collection.name
    assert pdf_import_service.collection.name == analytics_service.collection.name