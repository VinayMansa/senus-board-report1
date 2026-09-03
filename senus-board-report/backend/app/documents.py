"""
Live document ingestion — the piece that makes the platform dynamic rather
than a one-time snapshot. A user (e.g. the CFO, ahead of a Board meeting)
uploads a new filing (PDF or pasted text, such as the FY2026 half-year
report); it's run through the same AI extraction used to bootstrap the app,
but the result is NOT written to the database until a human reviews and
confirms it via /commit. This two-step extract-then-commit flow exists
because an LLM extraction of financial figures should never silently
overwrite what the Board Report shows without a check.
"""

from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy.orm import Session

from ..ai_extraction import extract_from_text
from ..database import get_db
from ..ingest import ingest_extraction_result
from ..models import UploadedDocument
from ..schemas import (
    ExtractionResult,
    DocumentExtractResponse,
    DocumentCommitRequest,
    DocumentCommitResponse,
    DocumentSummary,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_TEXT_CHARS = 60_000  # generous ceiling; keeps a single call well within model context


def _pdf_to_text(raw_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(raw_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail="Couldn't extract any text from that PDF — it may be a scanned image "
                   "without a text layer. Try pasting the text directly instead.",
        )
    return text


@router.post("/extract", response_model=DocumentExtractResponse)
async def extract_document(
    db: Session = Depends(get_db),
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
):
    if not file and not text:
        raise HTTPException(status_code=400, detail="Provide either a PDF file or pasted text.")

    if file:
        raw = await file.read()
        if file.filename and file.filename.lower().endswith(".pdf"):
            source_text = _pdf_to_text(raw)
        else:
            source_text = raw.decode("utf-8", errors="ignore")
        filename = file.filename
    else:
        source_text = text
        filename = None

    source_text = source_text[:MAX_TEXT_CHARS]

    doc = UploadedDocument(
        filename=filename,
        status="extracting",
        raw_text_excerpt=source_text[:2000],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        result = extract_from_text(source_text, incremental=True)
    except ValidationError as e:
        doc.status = "discarded"
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"AI extraction did not match the expected schema and was discarded: {e}",
        )
    except RuntimeError as e:
        doc.status = "discarded"
        db.commit()
        raise HTTPException(status_code=503, detail=str(e))

    warnings = []
    if not result.periods:
        warnings.append(
            "No financial period was identified in this document. Check that it contains "
            "a P&L / financial summary section, or paste that section directly."
        )

    doc.status = "pending_review"
    doc.fiscal_year_end = result.periods[0].fiscal_year_end if result.periods else None
    doc.extraction_json = result.model_dump_json()
    db.commit()

    return DocumentExtractResponse(
        document_id=doc.id, filename=filename, extraction=result, warnings=warnings
    )


@router.post("/{document_id}/commit", response_model=DocumentCommitResponse)
def commit_document(document_id: int, body: DocumentCommitRequest, db: Session = Depends(get_db)):
    doc = db.query(UploadedDocument).filter(UploadedDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if doc.status == "committed":
        raise HTTPException(status_code=409, detail="This upload has already been committed.")

    # Persist whatever the reviewer confirmed — which may differ from the raw
    # extraction if they corrected a figure — as the record of what was
    # actually written into the Board Report.
    doc.extraction_json = body.extraction.model_dump_json()
    summary = ingest_extraction_result(db, body.extraction, commit=False)

    doc.status = "committed"
    doc.committed_at = datetime.now(timezone.utc)
    db.commit()

    return DocumentCommitResponse(
        document_id=doc.id,
        status="committed",
        periods_written=summary["periods_written"],
        product_acv_written=summary["product_acv_written"],
        kpi_targets_written=summary["kpi_targets_written"],
        corporate_facts_written=summary["corporate_facts_written"],
    )


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)):
    rows = db.query(UploadedDocument).order_by(UploadedDocument.uploaded_at.desc()).all()
    return [
        DocumentSummary(
            id=r.id,
            filename=r.filename,
            uploaded_at=r.uploaded_at.isoformat(),
            status=r.status,
            fiscal_year_end=r.fiscal_year_end,
        )
        for r in rows
    ]


@router.delete("/{document_id}")
def discard_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(UploadedDocument).filter(UploadedDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if doc.status == "committed":
        raise HTTPException(
            status_code=409,
            detail="This upload has already been committed and affects live data; "
                   "it can't be discarded retroactively.",
        )
    doc.status = "discarded"
    db.commit()
    return {"status": "discarded", "document_id": doc.id}