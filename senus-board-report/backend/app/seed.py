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
        # Idempotent: wipe and reload so re-running seed.py is always safe.
        db.query(FinancialPeriod).delete()
        db.query(ProductACV).delete()
        db.query(KpiTarget).delete()
        db.query(CorporateFact).delete()

        for p in result.periods:
            db.add(FinancialPeriod(**p.model_dump()))

        for a in result.product_acv:
            db.add(ProductACV(**a.model_dump()))

        for k in result.kpi_targets:
            db.add(KpiTarget(**k.model_dump()))

        for f in result.corporate_facts:
            db.add(CorporateFact(**f.model_dump()))

        db.commit()
        print(
            f"[seed] Loaded {len(result.periods)} financial periods, "
            f"{len(result.product_acv)} product ACV rows, "
            f"{len(result.kpi_targets)} KPI targets, "
            f"{len(result.corporate_facts)} corporate facts into senus.db"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
