from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import metrics
from ..database import get_db
from ..models import FinancialPeriod, ProductACV, KpiTarget, CorporateFact
from ..schemas import (
    PeriodOut,
    GrowthMetrics,
    ProfitabilityMetrics,
    CashLiquidityMetrics,
    SolvencyMetrics,
    ReturnsMetrics,
)

router = APIRouter(prefix="/api/financials", tags=["financials"])


@router.get("/periods", response_model=list[PeriodOut])
def get_periods(db: Session = Depends(get_db)):
    rows = db.query(FinancialPeriod).order_by(FinancialPeriod.fiscal_year_end).all()
    return rows


@router.get("/corporate-facts")
def get_corporate_facts(db: Session = Depends(get_db)):
    rows = db.query(CorporateFact).all()
    return {r.key: r.value for r in rows}


@router.get("/kpi-targets")
def get_kpi_targets(db: Session = Depends(get_db)):
    rows = db.query(KpiTarget).all()
    return [
        {
            "kpi": r.kpi,
            "baseline": r.baseline,
            "target": r.target,
            "target_year": r.target_year,
            "description": r.description,
        }
        for r in rows
    ]


@router.get("/growth", response_model=GrowthMetrics)
def get_growth(db: Session = Depends(get_db)):
    periods = db.query(FinancialPeriod).all()
    acv = db.query(ProductACV).all()
    kpis = db.query(KpiTarget).all()
    return metrics.growth_metrics(periods, acv, kpis)


@router.get("/profitability", response_model=ProfitabilityMetrics)
def get_profitability(db: Session = Depends(get_db)):
    periods = db.query(FinancialPeriod).all()
    return metrics.profitability_metrics(periods)


@router.get("/cash-liquidity", response_model=CashLiquidityMetrics)
def get_cash_liquidity(db: Session = Depends(get_db)):
    periods = db.query(FinancialPeriod).all()
    return metrics.cash_liquidity_metrics(periods)


@router.get("/solvency", response_model=SolvencyMetrics)
def get_solvency(db: Session = Depends(get_db)):
    periods = db.query(FinancialPeriod).all()
    return metrics.solvency_metrics(periods)


@router.get("/returns", response_model=ReturnsMetrics)
def get_returns(db: Session = Depends(get_db)):
    periods = db.query(FinancialPeriod).all()
    acv = db.query(ProductACV).all()
    return metrics.returns_metrics(periods, acv)
