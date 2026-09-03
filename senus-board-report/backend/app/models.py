from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime
from datetime import datetime
from .database import Base


class FinancialPeriod(Base):
    """One fiscal year of consolidated financials, as extracted from the
    company's public Information Document."""

    __tablename__ = "financial_periods"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year_end = Column(String, unique=True, index=True)  # e.g. "2025-06-30"
    label = Column(String)  # e.g. "FY2025"

    turnover = Column(Float)
    gross_profit = Column(Float)
    operating_profit = Column(Float)
    profit_before_tax = Column(Float)
    profit_after_tax = Column(Float)
    net_assets_liabilities = Column(Float)
    retained_earnings = Column(Float)

    cash_flow_operating = Column(Float)
    cash_flow_investing = Column(Float)
    cash_flow_financing = Column(Float)
    net_change_in_cash = Column(Float)
    cash_start = Column(Float)
    cash_end = Column(Float)

    admin_expenses = Column(Float, nullable=True)
    rd_expenditure_pct_revenue = Column(Float, nullable=True)
    trade_debtors = Column(Float, nullable=True)
    trade_creditors = Column(Float, nullable=True)

    total_customers = Column(Integer, nullable=True)
    enterprise_customers = Column(Integer, nullable=True)
    independent_customers = Column(Integer, nullable=True)
    rd_customers = Column(Integer, nullable=True)

    revenue_pct_enterprise = Column(Float, nullable=True)
    revenue_pct_independent = Column(Float, nullable=True)
    revenue_pct_rd = Column(Float, nullable=True)
    revenue_pct_ireland = Column(Float, nullable=True)

    source_note = Column(Text, nullable=True)


class ProductACV(Base):
    """Average annual contract value by product line, for a given fiscal year."""

    __tablename__ = "product_acv"

    id = Column(Integer, primary_key=True, index=True)
    fiscal_year_end = Column(String, index=True)
    product = Column(String)  # Senus SOIL / Senus ERA / Senus TERRAIN
    avg_acv_enterprise = Column(Float)
    subscription_range_low = Column(Float, nullable=True)
    subscription_range_high = Column(Float, nullable=True)


class KpiTarget(Base):
    """Board-approved strategic targets under the 'Senus 2030' plan."""

    __tablename__ = "kpi_targets"

    id = Column(Integer, primary_key=True, index=True)
    kpi = Column(String)
    baseline = Column(String)
    target = Column(String)
    target_year = Column(String)
    description = Column(Text)


class CorporateFact(Base):
    """Misc. corporate/capital-structure facts used in the report header."""

    __tablename__ = "corporate_facts"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True)
    value = Column(String)


class InsightCache(Base):
    """Cached AI-generated commentary so we don't re-call the model on every
    page load. Keyed by the section it was generated for."""

    __tablename__ = "insight_cache"

    id = Column(Integer, primary_key=True, index=True)
    section = Column(String, unique=True, index=True)
    content = Column(Text)
    model = Column(String, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    is_fallback = Column(Boolean, default=False)
