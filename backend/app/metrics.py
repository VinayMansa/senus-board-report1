"""
Derived-metrics engine.

Takes the raw, AI-extracted financial periods stored in the database and
computes the board-report metrics requested in the assignment brief:
Growth & Revenue, Profitability, Cash & Liquidity, Solvency & Leverage,
and Returns. Every metric that relies on an assumption (because the
underlying figure isn't disclosed in the source Information Document) is
computed here in one place and paired with an explicit note explaining
the assumption, so the UI can surface it rather than presenting an
estimate as a disclosed fact.
"""

from datetime import date
from typing import List, Optional

from .models import FinancialPeriod, ProductACV, KpiTarget


def _sorted_periods(periods: List[FinancialPeriod]) -> List[FinancialPeriod]:
    return sorted(periods, key=lambda p: p.fiscal_year_end)


def _parse_date(iso_str: str) -> Optional[date]:
    try:
        return date.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return None


def _mom_growth(periods: List[FinancialPeriod]) -> dict:
    """Month-over-month revenue growth is only meaningful between two
    periods whose end-dates are ~1 month apart. The source Information
    Document only discloses ANNUAL figures (FY2024, FY2025 — 12 months
    apart), so MoM is genuinely not computable from it. This function is
    written to work automatically the moment monthly management accounts
    are uploaded via the Upload Report flow (which accepts any period
    end-date, not just fiscal year-ends) — no code change needed then."""
    if len(periods) < 2:
        return {"mom_revenue_growth_pct": None, "mom_note": (
            "Not available — at least two periods are needed to compute month-over-month growth."
        )}

    latest, previous = periods[-1], periods[-2]
    d1, d2 = _parse_date(previous.fiscal_year_end), _parse_date(latest.fiscal_year_end)
    if not d1 or not d2:
        return {"mom_revenue_growth_pct": None, "mom_note": "Not available — period dates could not be parsed."}

    gap_days = (d2 - d1).days
    if not (20 <= gap_days <= 45):
        return {
            "mom_revenue_growth_pct": None,
            "mom_note": (
                f"Not available — the two most recent periods on file ({previous.label} \u2192 {latest.label}) "
                f"are {gap_days} days apart, not ~1 month. The source Information Document discloses annual "
                "(FY-end) figures only. Upload monthly management accounts via 'Upload Report' and this metric "
                "populates automatically \u2014 no configuration needed."
            ),
        }

    if not previous.turnover:
        return {"mom_revenue_growth_pct": None, "mom_note": "Not available — prior period revenue is zero or missing."}

    mom = round((latest.turnover - previous.turnover) / previous.turnover * 100, 1)
    return {
        "mom_revenue_growth_pct": mom,
        "mom_note": f"Month-over-month revenue growth, {previous.label} \u2192 {latest.label}.",
    }


def growth_metrics(periods: List[FinancialPeriod], acv_rows: List[ProductACV], kpi_targets: List[KpiTarget]) -> dict:
    periods = _sorted_periods(periods)
    labels = [p.label for p in periods]
    revenue = [p.turnover for p in periods]

    yoy = None
    if len(periods) >= 2 and periods[-2].turnover:
        yoy = round((periods[-1].turnover - periods[-2].turnover) / periods[-2].turnover * 100, 1)

    cagr_target = 50.0
    for k in kpi_targets:
        if k.kpi == "Revenue Growth":
            import re
            m = re.search(r"(\d+)", k.target)
            if m:
                cagr_target = float(m.group(1))

    revenue_by_channel = {}
    revenue_by_geography = {}
    for p in periods:
        if p.revenue_pct_enterprise is not None:
            revenue_by_channel[p.label] = {
                "Enterprise": p.revenue_pct_enterprise,
                "Independent": p.revenue_pct_independent,
                "R&D": p.revenue_pct_rd,
            }
        if p.revenue_pct_ireland is not None:
            revenue_by_geography[p.label] = {
                "Ireland": p.revenue_pct_ireland,
                "Outside Ireland": round(100 - p.revenue_pct_ireland, 1),
            }

    mom = _mom_growth(periods)

    return {
        "periods": labels,
        "revenue": revenue,
        "revenue_yoy_growth_pct": yoy,
        "cagr_target_pct": cagr_target,
        "customers_total": [p.total_customers for p in periods],
        "revenue_by_channel": revenue_by_channel,
        "revenue_by_geography": revenue_by_geography,
        "product_acv": [
            {
                "fiscal_year_end": a.fiscal_year_end,
                "product": a.product,
                "avg_acv_enterprise": a.avg_acv_enterprise,
                "subscription_range_low": a.subscription_range_low,
                "subscription_range_high": a.subscription_range_high,
            }
            for a in acv_rows
        ],
        "mom_revenue_growth_pct": mom["mom_revenue_growth_pct"],
        "mom_note": mom["mom_note"],
        "bookings_note": (
            "Not disclosed. The source Information Document reports recognised revenue "
            "(\u20ac836,991 FY2025) and Enterprise Average Contract Value by product, but not new "
            "bookings / total contract value signed in the period. The Company describes tracking "
            "\u2018leads generated, prospects, projects priced and contracts won\u2019 through its sales funnel "
            "internally (Section 5.1.2), which would be the source for a Bookings metric \u2014 this would "
            "require a CRM/pipeline data connector, not a financial filing, to populate reliably."
        ),
    }



def profitability_metrics(periods: List[FinancialPeriod]) -> dict:
    periods = _sorted_periods(periods)
    labels = [p.label for p in periods]

    gross_margin = [round(p.gross_profit / p.turnover * 100, 1) for p in periods]
    operating_margin = [round(p.operating_profit / p.turnover * 100, 1) for p in periods]
    # EBITDA proxy: no separate D&A is disclosed anywhere in the source Information
    # Document, and investing cash outflows are minimal (<€35k in both years),
    # consistent with an asset-light software business. We therefore approximate
    # EBITDA as Operating Profit. This is an explicit, documented assumption.
    ebitda_proxy = [p.operating_profit for p in periods]
    ebitda_margin = operating_margin
    net_margin = [round(p.profit_after_tax / p.turnover * 100, 1) for p in periods]

    cost_breakdown = {}
    for p in periods:
        cost_of_sales = round(p.turnover - p.gross_profit, 0)
        entry = {"Cost of Sales": cost_of_sales}
        if p.admin_expenses is not None:
            entry["Administrative Expenses"] = p.admin_expenses
        cost_breakdown[p.label] = entry

    return {
        "periods": labels,
        "gross_margin_pct": gross_margin,
        "operating_margin_pct": operating_margin,
        "ebitda_proxy": ebitda_proxy,
        "ebitda_margin_pct": ebitda_margin,
        "net_margin_pct": net_margin,
        "cost_breakdown": cost_breakdown,
        "assumption_note": (
            "No depreciation & amortisation line is disclosed separately in the source "
            "Information Document. Given minimal investing cash outflows (\u20ac3,451 in FY2025; "
            "\u20ac33,472 in FY2024), consistent with an asset-light software business, EBITDA is "
            "approximated as Operating Profit. This is a modelling assumption, not a disclosed "
            "figure, and should be refined once full statutory accounts (with a fixed asset note) "
            "are available."
        ),
    }


def cash_liquidity_metrics(periods: List[FinancialPeriod]) -> dict:
    periods = _sorted_periods(periods)
    labels = [p.label for p in periods]
    latest = periods[-1]

    monthly_burn = None
    runway = None
    if latest.cash_flow_operating and latest.cash_flow_operating < 0:
        monthly_burn = round(abs(latest.cash_flow_operating) / 12, 0)
        runway = round(latest.cash_end / monthly_burn, 1) if monthly_burn else None

    working_capital = [
        round((p.trade_debtors or 0) - (p.trade_creditors or 0), 0) for p in periods
    ]

    bridge = {}
    for p in periods:
        ebitda_proxy = p.operating_profit
        wc_and_other = round(p.cash_flow_operating - ebitda_proxy, 0)
        fcf = round(p.cash_flow_operating + p.cash_flow_investing, 0)
        bridge[p.label] = {
            "EBITDA (proxy)": ebitda_proxy,
            "Working capital & other movements": wc_and_other,
            "Operating Cash Flow": p.cash_flow_operating,
            "Capex / Investing": p.cash_flow_investing,
            "Free Cash Flow": fcf,
        }

    return {
        "periods": labels,
        "cash_end": [p.cash_end for p in periods],
        "operating_cash_flow": [p.cash_flow_operating for p in periods],
        "investing_cash_flow": [p.cash_flow_investing for p in periods],
        "financing_cash_flow": [p.cash_flow_financing for p in periods],
        "monthly_cash_burn": monthly_burn,
        "cash_runway_months": runway,
        "trade_working_capital": working_capital,
        "ebitda_to_fcf_bridge": bridge,
        "assumption_note": (
            f"Cash runway ({runway} months, based on FY2025 closing cash of \u20ac{latest.cash_end:,.0f} "
            f"and an average FY2025 monthly operating cash burn of \u20ac{monthly_burn:,.0f}) reflects the "
            "position AS AT 30 June 2025 only. It excludes the \u20ac1.1m 2025 Private Placement completed "
            "in December 2025 (post year-end) and the \u20ac100,000 SBCI-backed term loan drawn during "
            "FY2025, both of which materially improve the Company's actual liquidity position beyond "
            "what this trailing operating metric implies."
        ),
    }


def solvency_metrics(periods: List[FinancialPeriod]) -> dict:
    periods = _sorted_periods(periods)
    labels = [p.label for p in periods]
    latest = periods[-1]

    # Illustrative DSCR: the source document discloses that a new \u20ac100,000
    # SBCI-backed term loan was drawn in FY2025, but does not disclose its
    # interest rate or amortisation schedule. We estimate annual debt service
    # using a standard 5-year amortising structure at an illustrative 6% p.a.
    # rate typical of SBCI-backed SME lending, and flag this explicitly as an
    # assumption rather than a disclosed fact.
    principal = 100000.0
    rate = 0.06
    term_years = 5
    annuity_factor = (rate * (1 + rate) ** term_years) / ((1 + rate) ** term_years - 1)
    illustrative_annual_debt_service = round(principal * annuity_factor, 0)

    cfads = latest.cash_flow_operating  # cash flow available for debt service (proxy)
    dscr = round(cfads / illustrative_annual_debt_service, 2) if illustrative_annual_debt_service else None

    if cfads is not None and cfads < 0:
        dscr_status = "Below 1.0x (operating cash flow is negative)"
    elif dscr is not None and dscr >= 1.0:
        dscr_status = f"{dscr}x — covered"
    elif dscr is not None:
        dscr_status = f"{dscr}x — below 1.0x"
    else:
        dscr_status = "Not calculable"

    return {
        "periods": labels,
        "net_assets_liabilities": [p.net_assets_liabilities for p in periods],
        "new_debt_drawn": principal,
        "dscr_status": dscr_status,
        "dscr_note": (
            f"Illustrative only: assumes the disclosed \u20ac100,000 SBCI-backed term loan amortises over "
            f"5 years at 6% p.a. (\u2248\u20ac{illustrative_annual_debt_service:,.0f}/yr debt service) \u2014 the actual "
            "rate and term are not disclosed in the source document. Against FY2025 operating cash flow "
            f"of \u20ac{cfads:,.0f}, the Company does not currently generate sufficient cash from operations "
            "to service debt without recourse to equity funding (the \u20ac1.1m 2025 Private Placement) or "
            "further financing. Credit providers should request the actual loan agreement terms."
        ),
        "gearing_note": (
            f"Net (liabilities)/assets moved from \u20ac{periods[-2].net_assets_liabilities:,.0f} ({periods[-2].label}) to "
            f"\u20ac{latest.net_assets_liabilities:,.0f} ({latest.label}) \u2014 i.e. the Company had negative shareholders' "
            "equity at 30 June 2025 due to accumulated losses. Conventional gearing (Debt/Equity) is not "
            "meaningful with negative equity. This pre-dates the December 2025 \u20ac1.1m Private Placement "
            "and Euronext Admission, which the Directors state was completed to strengthen the balance "
            "sheet ahead of the next growth phase \u2014 post year-end capital position is materially stronger."
        ),
    }


def returns_metrics(periods: List[FinancialPeriod], acv_rows: List[ProductACV]) -> dict:
    periods = _sorted_periods(periods)
    labels = [p.label for p in periods]

    trend = {a.product: a.avg_acv_enterprise for a in acv_rows}

    # Illustrative ROCE. Capital Employed = Equity + Non-current liabilities
    # is the standard proxy when a full balance sheet isn't available. The
    # source document discloses Net (Liabilities)/Assets (i.e. equity)
    # directly for both years, but only the MOVEMENT in non-current
    # liabilities (+\u20ac83,655 in FY2025, "following drawdown of a new bank
    # loan"), not the absolute balance in either year. We assume FY2024
    # non-current liabilities were ~\u20ac0 (a pre-loan, pre-revenue-scale
    # company) and that the FY2025 balance equals that disclosed movement \u2014
    # i.e. the new loan IS substantially the FY2025 non-current liabilities
    # figure. This is flagged as an estimate, not a disclosed fact.
    assumed_noncurrent_liabilities = {periods[0].label: 0.0} if periods else {}
    if len(periods) >= 2:
        assumed_noncurrent_liabilities[periods[-1].label] = 83655.0

    roce_pct = []
    capital_employed = []
    for p in periods:
        ncl = assumed_noncurrent_liabilities.get(p.label, 0.0)
        ce = p.net_assets_liabilities + ncl
        capital_employed.append(round(ce, 0))
        if ce and abs(ce) > 1:
            roce_pct.append(round(p.operating_profit / ce * 100, 1))
        else:
            roce_pct.append(None)

    latest_roce = roce_pct[-1] if roce_pct else None
    roce_status = f"{latest_roce}% (illustrative estimate)" if latest_roce is not None else "Not calculable"

    return {
        "periods": labels,
        "roce_pct": roce_pct,
        "capital_employed": capital_employed,
        "roce_status": roce_status,
        "roce_note": (
            "Illustrative estimate, not a precise disclosed figure. Capital Employed = Net Assets/"
            "(Liabilities) + Non-current Liabilities. The source document discloses equity directly for "
            "both years, but only the MOVEMENT in non-current liabilities (+\u20ac83,655 in FY2025, following "
            "drawdown of the new SBCI-backed term loan), not the absolute balance in either year. This "
            "estimate assumes FY2024 non-current liabilities were negligible (pre-loan) and that the "
            "FY2025 balance equals that disclosed movement. Under this assumption, ROCE is extremely "
            "negative in both years \u2014 driven as much by a very small capital-employed base (the Company "
            "had \u20ac15,575 of NET LIABILITIES, not assets, at FY2025 year-end) as by the operating loss "
            "itself. Treat the magnitude with caution; the direction (deeply negative) is robust to the "
            "assumption, the precise number is not. Request the full statutory balance sheet for FY2026 "
            "reporting to replace this estimate with a precise figure."
        ),
        "avg_acv_enterprise_trend": trend,
    }