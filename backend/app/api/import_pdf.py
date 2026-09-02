from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.import_result import ImportResult
from app.services.pdf_import_service import import_pdf

router = APIRouter(prefix="/api/import", tags=["import"])

_MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB -- generous for a statement PDF


@router.post("/pdf", response_model=ImportResult)
async def import_pdf_statement(file: UploadFile = File(...)):
    """
    Accept a single PDF transaction statement, parse it, and insert any
    recognized transactions into MongoDB (same collection/flow as every
    other transaction in this app).

    Validation is deliberately done here at the API boundary (content
    type, file size) rather than inside the parsing service, which stays
    focused purely on "given PDF bytes, extract transactions."
    """
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="The uploaded file is too large.")

    # A very cheap, real check that this is actually a PDF (content_type is
    # client-supplied and easy to spoof/misconfigure) -- PDF files always
    # start with this magic header.
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    try:
        return import_pdf(file_bytes)
    except Exception:
        # Catch-all so a malformed/corrupt PDF or an unexpected parsing
        # error never surfaces a raw traceback to the client -- same
        # pattern as app/api/ml.py's catch-all.
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the PDF.",
        )