"""
Parses a PhonePe/Paytm/GPay-style transaction statement PDF into Transaction
records and inserts them into the same MongoDB collection used everywhere
else in this app.

IMPORTANT, READ FIRST:
This is a heuristic, best-effort MVP parser -- not an officially certified
parser for any specific provider's export format. PhonePe/Paytm/GPay don't
publish a stable, versioned schema for their statement PDFs, and the exact
layout can vary by app version, region, and export settings. The approach
here is a reasonably generic "date ... description ... amount" line pattern
that these providers' statements commonly follow, with graceful skipping of
anything that doesn't match rather than guessing.

DESIGN:
1. extract_text_from_pdf() -- pulls plain text out of the PDF using
   pdfplumber (see requirements.txt for why this library was chosen).
2. parse_statement_text() -- scans each line for a date pattern AND an
   amount pattern. A line only counts as a transaction candidate if BOTH
   are found; this avoids misclassifying headers/footers/disclaimers
   (which often contain a date or a number, but rarely both in the same
   line as a filled-in transaction row) as transactions.
3. build_transaction() -- turns one parsed row into a real Transaction
   object (see app/schemas/transaction.py), using the ACTUAL date parsed
   from the statement as created_at (not "now") -- this is what lets the
   existing Spending Trend analytics show real multi-day data instead of
   everything collapsing onto the upload date.
4. import_pdf() -- orchestrates the above, then bulk-inserts into the
   existing "transactions" collection with per-row duplicate detection.

WHY Transaction (not TransactionCreate) IS USED DIRECTLY:
TransactionCreate (the schema POST /api/transactions validates against)
deliberately has no created_at field -- a client can't backdate a
transaction through that endpoint. But Transaction itself (the full stored
record) has created_at as a Field with a default_factory, which is only
applied when the field is *omitted*. Constructing Transaction(...,
created_at=parsed_date, transaction_id=deterministic_id) explicitly here
uses that same class exactly as designed, without touching
app/schemas/transaction.py at all.
"""

import re
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from typing import List

import pdfplumber
from pymongo.errors import BulkWriteError

from app.db.mongodb import db
from app.schemas.import_result import ImportResult
from app.schemas.transaction import (
    Transaction,
    TransactionSource,
    TransactionStatus,
    TransactionType,
)

# Reuses the existing MongoDB connection (app/db/mongodb.py) and the SAME
# "transactions" collection every other service already writes to and
# reads from -- no new connection, no separate collection.
collection = db["transactions"]


# --- Date patterns -----------------------------------------------------
# Each entry is (regex, strptime format). Tried in order; the first that
# matches AND successfully parses wins. Covers the handful of date styles
# commonly seen across PhonePe/Paytm/GPay statement exports.
_DATE_PATTERNS = [
    (re.compile(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"), "%d %b %Y"),
    (re.compile(r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"), "%b %d %Y"),
    (re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}"), "%d/%m/%Y"),
    (re.compile(r"\d{4}-\d{1,2}-\d{1,2}"), "%Y-%m-%d"),
]

# Currency-prefixed amount, e.g. "Rs.1,499.00", "₹342.50", "INR 1,200".
# Group 2 captures just the numeric portion.
_AMOUNT_PATTERN = re.compile(
    r"(₹|Rs\.?|INR|\$|USD|€|EUR)\s?([\d,]+\.?\d*)", re.IGNORECASE
)

_CURRENCY_SYMBOL_MAP = {
    "₹": "INR", "rs": "INR", "rs.": "INR", "inr": "INR",
    "$": "USD", "usd": "USD",
    "€": "EUR", "eur": "EUR",
}

_DEBIT_KEYWORDS = re.compile(r"\b(debit|debited|paid to|paid)\b", re.IGNORECASE)
_CREDIT_KEYWORDS = re.compile(r"\b(credit|credited|received from|received)\b", re.IGNORECASE)
_REFUND_KEYWORDS = re.compile(r"\brefund", re.IGNORECASE)
_CHARGEBACK_KEYWORDS = re.compile(r"\bchargeback", re.IGNORECASE)
_FAILED_KEYWORDS = re.compile(r"\b(fail|failed|unsuccessful)\b", re.IGNORECASE)
_PENDING_KEYWORDS = re.compile(r"\bpending\b", re.IGNORECASE)

_PAYMENT_METHOD_KEYWORDS = [
    (re.compile(r"\bupi\b", re.IGNORECASE), "upi"),
    (re.compile(r"\bcard\b", re.IGNORECASE), "card"),
    (re.compile(r"\bwallet\b", re.IGNORECASE), "wallet"),
    (re.compile(r"\bnet ?banking\b", re.IGNORECASE), "netbanking"),
    (re.compile(r"\bbank transfer\b", re.IGNORECASE), "bank_transfer"),
]

# Rough keyword -> category map for real (PhonePe/Paytm/GPay-style)
# consumer statement lines. Checked in order, first match wins. Falls back
# to "Uncategorized" when nothing matches -- this is a best-effort,
# deterministic convenience, not a claim of certified merchant
# classification. Labels are Title Case so they render directly in the
# "Where Your Money Went" UI without any further frontend transformation.
#
# This list is intentionally broader than a single merchant per category
# (e.g. many generic food-item/dish keywords) because small UPI QR
# payments to local vendors (canteens, stalls, etc.) often carry a
# free-text note like "Pasta Grilled" rather than a recognizable brand
# name -- there is no registry of such notes to look up, so common food
# words are matched directly as a deterministic, explainable heuristic.
_CATEGORY_KEYWORDS = [
    (re.compile(
        r"meesho|amazon|flipkart|myntra|ajio|nykaa|shopclues|shopping",
        re.IGNORECASE,
    ), "Shopping"),
    (re.compile(
        r"swiggy|zomato|restaurant|cafe|dominos|canteen|mess|dhaba|"
        r"hotel|bakery|sweet|biryani|pizza|burger|sandwich|dosa|thali|"
        r"chaat|roll|noodles|tandoor|juice|shake|pasta|grilled|tea|"
        r"coffee|food",
        re.IGNORECASE,
    ), "Food"),
    (re.compile(
        r"general store|kirana|grocery|groceries|bigbasket|supermarket|dmart",
        re.IGNORECASE,
    ), "Groceries"),
    (re.compile(
        r"recharge|prepaid|postpaid|jio|airtel|\bvi\b|vodafone|mobile bill",
        re.IGNORECASE,
    ), "Mobile Recharge"),
    (re.compile(
        r"shadowfax|dunzo|porter|delhivery|ekart|bluedart|courier|delivery",
        re.IGNORECASE,
    ), "Delivery"),
    (re.compile(
        r"uber|ola|rapido|irctc|flight|train|travel|metro|fuel|petrol|diesel",
        re.IGNORECASE,
    ), "Travel"),
    (re.compile(
        r"electricity|water bill|gas board|utility|utilities|broadband|wifi",
        re.IGNORECASE,
    ), "Utilities"),
    (re.compile(
        r"netflix|spotify|prime|subscription|hotstar|youtube",
        re.IGNORECASE,
    ), "Subscriptions"),
    (re.compile(r"\btransfer(red)?\b|self transfer", re.IGNORECASE), "Transfers"),
    (re.compile(r"office|stationery|supplies", re.IGNORECASE), "Office Supplies"),
]


class ParsedRow:
    """One transaction candidate line, after successful parsing."""

    def __init__(self, date: datetime, amount: float, currency: str,
                 transaction_type: TransactionType, status: TransactionStatus,
                 payment_method: str, category: str, description: str):
        self.date = date
        self.amount = amount
        self.currency = currency
        self.transaction_type = transaction_type
        self.status = status
        self.payment_method = payment_method
        self.category = category
        self.description = description


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract plain text from every page of the PDF.
    Plain extract_text() (not layout=True) is used deliberately: for the
    flexible regex-based line parsing this module does, plain mode gives
    cleaner, whitespace-normalized lines. layout=True instead preserves
    exact character positions, which introduces long runs of padding
    whitespace and blank lines that don't help this parser and would only
    need to be filtered back out.
    """
    text_parts = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def _find_date(line: str):
    """Return (match_object, parsed_datetime) for the first date pattern
    that matches AND successfully parses, or None if none do."""
    for pattern, fmt in _DATE_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        raw = match.group(0).replace(",", "")
        try:
            parsed = datetime.strptime(raw, fmt.replace(",", ""))
        except ValueError:
            continue
        # Statements rarely include a time; default to midday UTC so a
        # timezone conversion elsewhere can never accidentally roll the
        # date over to the previous/next day.
        parsed = parsed.replace(hour=12, tzinfo=timezone.utc)
        return match, parsed
    return None


def _infer_currency(symbol: str) -> str:
    return _CURRENCY_SYMBOL_MAP.get(symbol.strip().lower(), "INR")


def _infer_payment_method(line: str) -> str:
    for pattern, method in _PAYMENT_METHOD_KEYWORDS:
        if pattern.search(line):
            return method
    # PhonePe/Paytm/GPay statements are predominantly UPI-based; this is a
    # reasonable MVP default when no explicit method is mentioned on the line.
    return "upi"


def _infer_category(description: str) -> str:
    for pattern, category in _CATEGORY_KEYWORDS:
        if pattern.search(description):
            return category
    return "Uncategorized"


def _infer_transaction_type(line: str, is_credit: bool) -> TransactionType:
    if _CHARGEBACK_KEYWORDS.search(line):
        return TransactionType.CHARGEBACK
    if _REFUND_KEYWORDS.search(line):
        return TransactionType.REFUND
    if is_credit:
        # Simplification: the schema has no generic "incoming funds" type,
        # so an incoming/credited line is treated as a refund. This won't
        # be accurate for e.g. peer-to-peer money received that isn't
        # actually a refund, but it's the closest fit available and is
        # documented here rather than silently assumed.
        return TransactionType.REFUND
    return TransactionType.PAYMENT


def _infer_status(line: str) -> TransactionStatus:
    if _FAILED_KEYWORDS.search(line):
        return TransactionStatus.FAILED
    if _PENDING_KEYWORDS.search(line):
        return TransactionStatus.PENDING
    # Statements typically only itemize settled transactions; successful
    # is the reasonable default when no explicit status wording is present.
    return TransactionStatus.SUCCESSFUL


def _remove_match(text: str, match) -> str:
    return text[:match.start()] + text[match.end():]


def parse_statement_text(text: str):
    """
    Parse extracted PDF text into ParsedRow objects.
    Returns (parsed_rows, failed_row_count, warnings).

    Lines with neither a date nor an amount are silently ignored (headers,
    footers, disclaimers, page numbers, etc. -- not counted as failures).
    A line is only a "failed row" if it looked like a transaction
    (had both a date and an amount) but something about it couldn't be
    turned into a valid record.
    """
    parsed_rows: List[ParsedRow] = []
    failed_row_count = 0
    warnings: List[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        date_result = _find_date(line)
        amount_match = _AMOUNT_PATTERN.search(line)

        if not date_result or not amount_match:
            continue  # not a transaction candidate line -- ignore quietly

        date_match, parsed_date = date_result

        try:
            amount = float(amount_match.group(2).replace(",", ""))
            if amount <= 0:
                raise ValueError("non-positive amount")

            currency = _infer_currency(amount_match.group(1))

            # Description = whatever's between the date and the amount,
            # with the matched date/amount text and Debit/Credit keyword
            # noise stripped out.
            start = date_match.end()
            end = amount_match.start()
            if end <= start:
                # Amount appeared before the date on this line -- unusual
                # layout; fall back to the whole line minus both matches.
                description = _AMOUNT_PATTERN.sub("", _remove_match(line, date_match)).strip()
            else:
                description = line[start:end].strip()
            description = re.sub(r"\s+", " ", description)
            description = re.sub(r"\b(debit|credit)\b", "", description, flags=re.IGNORECASE).strip(" :-")

            if not description:
                description = "unlabeled_transaction"

            is_credit = bool(_CREDIT_KEYWORDS.search(line)) and not bool(_DEBIT_KEYWORDS.search(line))

            category = _infer_category(description)
            # A credited/received line with no recognizable merchant
            # keyword (i.e. still "Uncategorized" after the keyword pass)
            # is almost always a peer-to-peer UPI transfer (e.g. "Received
            # from Rohan Mehta"), not a real merchant category -- "Transfers"
            # communicates that far more clearly on the dashboard.
            if category == "Uncategorized" and is_credit:
                category = "Transfers"

            parsed_rows.append(ParsedRow(
                date=parsed_date,
                amount=amount,
                currency=currency,
                transaction_type=_infer_transaction_type(line, is_credit),
                status=_infer_status(line),
                payment_method=_infer_payment_method(line),
                category=category,
                description=description,
            ))
        except (ValueError, IndexError):
            failed_row_count += 1

    if not parsed_rows and failed_row_count == 0:
        warnings.append("No transaction rows were found in this PDF.")
    if failed_row_count > 0:
        warnings.append(
            f"{failed_row_count} line(s) looked like a transaction but could not be parsed."
        )

    return parsed_rows, failed_row_count, warnings


def _normalize_merchant_id(description: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_")
    return slug[:60] if slug else "unknown_merchant"


def _statement_id(file_bytes: bytes) -> str:
    """Stable identifier for one exact uploaded PDF."""
    return f"stmt_{sha256(file_bytes).hexdigest()[:32]}"


def _deterministic_transaction_id(row: ParsedRow) -> str:
    """
    Same input row -> same ID, every time. This is what lets re-uploading
    the same PDF be safely skipped as duplicates (via the existing unique
    index on transaction_id in app/db/mongodb.py) rather than creating a
    second copy of every transaction.
    """
    fingerprint = f"{row.date.date().isoformat()}|{row.amount:.2f}|{row.description}|{row.transaction_type.value}"
    digest = sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"pdf_{digest[:32]}"


def build_transaction(row: ParsedRow, statement_id: str | None = None) -> Transaction:
    """Turn one ParsedRow into a full Transaction record ready to insert."""
    merchant_id = _normalize_merchant_id(row.description)
    return Transaction(
        merchant_id=merchant_id,
        amount=row.amount,
        currency=row.currency,
        transaction_type=row.transaction_type,
        status=row.status,
        payment_method=row.payment_method,
        # No auth/user system exists in this app yet (by design, per
        # project scope) -- this is a placeholder, not a real customer
        # identity, documented here rather than silently invented.
        customer_id="statement_import",
        category=row.category,
        transaction_id=_deterministic_transaction_id(row),
        created_at=row.date,
        # Tagged explicitly so the analytics layer can identify this as
        # the user's real financial data -- see TransactionSource in
        # app/schemas/transaction.py.
        source=TransactionSource.STATEMENT_IMPORT,
        statement_id=statement_id,
    )


def import_pdf(file_bytes: bytes) -> ImportResult:
    """Extract, parse and safely import one statement PDF.

    The exact PDF bytes define a stable statement_id. Re-uploading the same
    statement therefore selects the same dashboard dataset even when every
    transaction is already a duplicate. Legacy PDF-import rows (identified
    by the historical ``pdf_`` transaction_id prefix) are backfilled with
    source=statement_import and this statement_id when they match the parsed
    transaction IDs.
    """
    statement_id = _statement_id(file_bytes)
    text = extract_text_from_pdf(file_bytes)
    parsed_rows, failed_row_count, warnings = parse_statement_text(text)

    if not parsed_rows:
        return ImportResult(
            statement_id=statement_id,
            imported=0,
            skipped_duplicates=0,
            failed_rows=failed_row_count,
            warnings=warnings,
            errors=[],
        )

    transactions = [build_transaction(row, statement_id=statement_id) for row in parsed_rows]
    documents = [t.model_dump() for t in transactions]
    transaction_ids = [t.transaction_id for t in transactions]

    # Repair records imported by the previous version of PayPilot. These
    # rows already have deterministic pdf_ IDs but no source/statement_id.
    # Updating only those exact IDs is safe and makes duplicate re-uploading
    # work without deleting any user data.
    collection.update_many(
        {
            "$and": [
                {"transaction_id": {"$in": transaction_ids}},
                {"transaction_id": {"$regex": r"^pdf_"}},
            ]
        },
        {"$set": {"source": TransactionSource.STATEMENT_IMPORT.value,
                  "statement_id": statement_id}},
    )

    imported = 0
    skipped_duplicates = 0
    errors: List[str] = []

    try:
        result = collection.insert_many(documents, ordered=False)
        imported = len(result.inserted_ids)
    except BulkWriteError as bwe:
        details = bwe.details or {}
        imported = details.get("nInserted", 0)
        write_errors = details.get("writeErrors", [])
        for err in write_errors:
            if err.get("code") == 11000:
                skipped_duplicates += 1
            else:
                errors.append("One row failed to import due to a database error.")

    return ImportResult(
        statement_id=statement_id,
        imported=imported,
        skipped_duplicates=skipped_duplicates,
        failed_rows=failed_row_count,
        warnings=warnings,
        errors=errors,
    )
