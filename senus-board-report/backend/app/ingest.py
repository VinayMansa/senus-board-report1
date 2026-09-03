"""
Upsert logic for writing a validated ExtractionResult into the database.

Shared by app/seed.py (offline bootstrap from the committed Information
Document extraction) and routers/documents.py (live, in-app uploads of new
filings). Upserting rather than overwriting means the Board Report
accumulates periods over time — uploading a new half-year filing adds a
period alongside FY2024/FY2025 rather than replacing them, and the
dashboard's charts and YoY comparisons extend automatically.
"""

from sqlalchemy.orm import Session

from .models import FinancialPeriod, ProductACV, KpiTarget, CorporateFact
from .schemas import ExtractionResult


def upsert_period(db: Session, period) -> FinancialPeriod:
    existing = db.query(FinancialPeriod).filter(
        FinancialPeriod.fiscal_year_end == period.fiscal_year_end
    ).first()
    data = period.model_dump()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        return existing
    row = FinancialPeriod(**data)
    db.add(row)
    return row


def upsert_product_acv(db: Session, acv) -> ProductACV:
    existing = db.query(ProductACV).filter(
        ProductACV.fiscal_year_end == acv.fiscal_year_end,
        ProductACV.product == acv.product,
    ).first()
    data = acv.model_dump()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        return existing
    row = ProductACV(**data)
    db.add(row)
    return row


def upsert_kpi_target(db: Session, kpi) -> KpiTarget:
    existing = db.query(KpiTarget).filter(KpiTarget.kpi == kpi.kpi).first()
    data = kpi.model_dump()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        return existing
    row = KpiTarget(**data)
    db.add(row)
    return row


def upsert_corporate_fact(db: Session, fact) -> CorporateFact:
    existing = db.query(CorporateFact).filter(CorporateFact.key == fact.key).first()
    data = fact.model_dump()
    if existing:
        existing.value = fact.value
        return existing
    row = CorporateFact(**data)
    db.add(row)
    return row


def ingest_extraction_result(db: Session, result: ExtractionResult, commit: bool = True) -> dict:
    """Upserts every row in an ExtractionResult. Returns a summary of what
    was written, for the caller to report back to the user."""
    for p in result.periods:
        upsert_period(db, p)
    for a in result.product_acv:
        upsert_product_acv(db, a)
    for k in result.kpi_targets:
        upsert_kpi_target(db, k)
    for f in result.corporate_facts:
        upsert_corporate_fact(db, f)

    if commit:
        db.commit()

    return {
        "periods_written": [p.fiscal_year_end for p in result.periods],
        "product_acv_written": len(result.product_acv),
        "kpi_targets_written": len(result.kpi_targets),
        "corporate_facts_written": len(result.corporate_facts),
    }