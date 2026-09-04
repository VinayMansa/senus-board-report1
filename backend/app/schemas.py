from pydantic import BaseModel, Field
from typing import Optional, List


# ---------------------------------------------------------------------------
# Extraction target schema. This is the exact shape we ask the LLM to return
# when parsing the raw source document (app/data/source_document.txt) into
# structured data. Keeping it as a Pydantic model lets us validate the
# model's output before it ever reaches the database.
# ---------------------------------------------------------------------------

class ExtractedPeriod(BaseModel):
    fiscal_year_end: str = Field(..., description="ISO date, e.g. 2025-06-30")
    label: str
    turnover: float
    gross_profit: float
    operating_profit: float
    profit_before_tax: float
    profit_after_tax: float
    net_assets_liabilities: float
    retained_earnings: float
    cash_flow_operating: float
    cash_flow_investing: float
    cash_flow_financing: float
    net_change_in_cash: float
    cash_start: float
    cash_end: float
    admin_expenses: Optional[float] = None
    rd_expenditure_pct_revenue: Optional[float] = None
    trade_debtors: Optional[float] = None
    trade_creditors: Optional[float] = None
    total_customers: Optional[int] = None
    enterprise_customers: Optional[int] = None
    independent_customers: Optional[int] = None
    rd_customers: Optional[int] = None
    revenue_pct_enterprise: Optional[float] = None
    revenue_pct_independent: Optional[float] = None
    revenue_pct_rd: Optional[float] = None
    revenue_pct_ireland: Optional[float] = None
    source_note: Optional[str] = None


class ExtractedProductACV(BaseModel):
    fiscal_year_end: str
    product: str
    avg_acv_enterprise: float
    subscription_range_low: Optional[float] = None
    subscription_range_high: Optional[float] = None


class ExtractedKpiTarget(BaseModel):
    kpi: str
    baseline: str
    target: str
    target_year: str
    description: str


class ExtractedCorporateFact(BaseModel):
    key: str
    value: str


class ExtractionResult(BaseModel):
    """Top-level object the LLM must return."""
    periods: List[ExtractedPeriod]
    product_acv: List[ExtractedProductACV]
    kpi_targets: List[ExtractedKpiTarget]
    corporate_facts: List[ExtractedCorporateFact]


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------

class PeriodOut(ExtractedPeriod):
    class Config:
        from_attributes = True


class MetricPoint(BaseModel):
    label: str
    value: Optional[float]
    unit: str = ""
    note: Optional[str] = None


class GrowthMetrics(BaseModel):
    periods: List[str]
    revenue: List[float]
    revenue_yoy_growth_pct: Optional[float]
    cagr_target_pct: float
    customers_total: List[Optional[int]]
    revenue_by_channel: dict
    revenue_by_geography: dict
    product_acv: List[ExtractedProductACV]
    mom_revenue_growth_pct: Optional[float]
    mom_note: str
    bookings_note: str


class ProfitabilityMetrics(BaseModel):
    periods: List[str]
    gross_margin_pct: List[float]
    operating_margin_pct: List[float]
    ebitda_proxy: List[float]
    ebitda_margin_pct: List[float]
    net_margin_pct: List[float]
    cost_breakdown: dict
    assumption_note: str


class CashLiquidityMetrics(BaseModel):
    periods: List[str]
    cash_end: List[float]
    operating_cash_flow: List[float]
    investing_cash_flow: List[float]
    financing_cash_flow: List[float]
    monthly_cash_burn: Optional[float]
    cash_runway_months: Optional[float]
    trade_working_capital: List[float]
    ebitda_to_fcf_bridge: dict
    assumption_note: str


class SolvencyMetrics(BaseModel):
    periods: List[str]
    net_assets_liabilities: List[float]
    new_debt_drawn: Optional[float]
    dscr_status: str
    dscr_note: str
    gearing_note: str


class ReturnsMetrics(BaseModel):
    periods: List[str]
    roce_pct: List[Optional[float]]
    capital_employed: List[float]
    roce_status: str
    roce_note: str
    avg_acv_enterprise_trend: dict


# ---------------------------------------------------------------------------
# Document upload / live extraction schemas
# ---------------------------------------------------------------------------

class DocumentExtractResponse(BaseModel):
    document_id: int
    filename: Optional[str]
    extraction: ExtractionResult
    warnings: List[str] = []


class DocumentCommitRequest(BaseModel):
    """The (possibly human-edited) extraction the reviewer confirms. Sent
    back exactly as ExtractionResult so the same Pydantic validation applies
    whether the numbers came straight from the model or were corrected by
    a person before commit."""
    extraction: ExtractionResult


class DocumentCommitResponse(BaseModel):
    document_id: int
    status: str
    periods_written: List[str]
    product_acv_written: int
    kpi_targets_written: int
    corporate_facts_written: int


class DocumentSummary(BaseModel):
    id: int
    filename: Optional[str]
    uploaded_at: str
    status: str
    fiscal_year_end: Optional[str]

    class Config:
        from_attributes = True


class InsightRequest(BaseModel):
    section: str


class InsightResponse(BaseModel):
    section: str
    content: str
    model: Optional[str]
    is_fallback: bool
    generated_at: str