from typing import List

from pydantic import BaseModel


class ImportResult(BaseModel):
    """
    Summary returned after attempting to import a statement PDF.

    - imported: rows successfully parsed and newly inserted into MongoDB
    - skipped_duplicates: rows that parsed fine but already existed
      (same deterministic transaction_id -- e.g. re-uploading the same PDF)
    - failed_rows: lines in the PDF that looked like they might be a
      transaction but couldn't be parsed with enough confidence to import
    - warnings: human-readable notes (e.g. "3 lines skipped: no date found")
    - errors: human-readable notes about hard failures during import,
      deliberately never containing a raw exception message or stack trace
    """
    imported: int
    skipped_duplicates: int
    failed_rows: int
    warnings: List[str] = []
    errors: List[str] = []