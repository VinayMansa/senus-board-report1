"""
Loads app/data/extracted_financials.json (the validated output of the AI
extraction pipeline, see ai_extraction.py) into the SQLite database.

Run:
    python -m app.seed
"""

import json
from pathlib import Path

from .database import Base, engine, SessionLocal
from .models import FinancialPeriod, ProductACV, KpiTarget, CorporateFact
from .schemas import ExtractionResult
from .ingest import ingest_extraction_result

DATA_PATH = Path(__file__).parent / "data" / "extracted_financials.json"


def seed():
    Base.metadata.create_all(bind=engine)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run `python -m app.ai_extraction` first "
            "(requires ANTHROPIC_API_KEY), or restore the committed extraction output."
        )

    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    result = ExtractionResult.model_validate(raw)  # re-validate before trusting it

    db = SessionLocal()
    try:
        # Wipe and reload so re-running the bootstrap seed is always safe and
        # deterministic. Live document uploads (routers/documents.py) use the
        # same ingest_extraction_result() function but WITHOUT wiping first —
        # they upsert alongside whatever's already in the database, so
        # uploading a new filing adds to the Board Report rather than
        # resetting it.
        db.query(FinancialPeriod).delete()
        db.query(ProductACV).delete()
        db.query(KpiTarget).delete()
        db.query(CorporateFact).delete()

        summary = ingest_extraction_result(db, result, commit=True)
        print(
            f"[seed] Loaded {len(summary['periods_written'])} financial periods "
            f"({summary['periods_written']}), {summary['product_acv_written']} product ACV rows, "
            f"{summary['kpi_targets_written']} KPI targets, "
            f"{summary['corporate_facts_written']} corporate facts into senus.db"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()