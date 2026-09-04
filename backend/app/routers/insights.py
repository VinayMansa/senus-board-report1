"""
AI-generated board commentary.

For each report section (overview, growth, profitability, cash, solvency,
returns) we assemble the actual computed metrics for that section and ask
Claude to write a short, board-appropriate narrative — the kind of "so
what" commentary a CFO would add above a chart. Results are cached in the
database (InsightCache) so we don't re-call the model on every page load;
POST /generate/{section} forces a regeneration.

If no LLM provider is configured (see app/llm_client.py — Groq's free tier
or Anthropic), we fall back to a clearly-labelled templated summary built
from the same metrics, so the dashboard is always usable end-to-end without
a key.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import metrics
from ..database import get_db
from ..llm_client import chat_json, current_model_label
from ..models import FinancialPeriod, ProductACV, KpiTarget, InsightCache
from ..schemas import InsightResponse

router = APIRouter(prefix="/api/insights", tags=["insights"])

SECTION_BUILDERS = {
    "growth": lambda db: metrics.growth_metrics(
        db.query(FinancialPeriod).all(), db.query(ProductACV).all(), db.query(KpiTarget).all()
    ),
    "profitability": lambda db: metrics.profitability_metrics(db.query(FinancialPeriod).all()),
    "cash": lambda db: metrics.cash_liquidity_metrics(db.query(FinancialPeriod).all()),
    "solvency": lambda db: metrics.solvency_metrics(db.query(FinancialPeriod).all()),
    "returns": lambda db: metrics.returns_metrics(db.query(FinancialPeriod).all(), db.query(ProductACV).all()),
}

SECTION_AUDIENCE_HINT = {
    "growth": "the Board and Equity Investors, who care about topline momentum against the Senus 2030 50% CAGR target",
    "profitability": "Management and the Board, who care about the path to the FY2028 EBITDA-positive target",
    "cash": "Credit Providers and the Board, who care about runway and cash discipline",
    "solvency": "Credit Providers, who care about debt service capacity and balance sheet strength",
    "returns": "Equity Investors, who care about capital efficiency and contract value trends",
}


def _fallback_text(section: str, data: dict) -> str:
    if section == "growth":
        return (
            f"Revenue grew {data.get('revenue_yoy_growth_pct')}% YoY to \u20ac{data['revenue'][-1]:,.0f} "
            f"in {data['periods'][-1]}, against a Senus 2030 target CAGR of {data['cagr_target_pct']}%. "
            "(Fallback summary — configure GROQ_API_KEY (free) or ANTHROPIC_API_KEY for AI-generated narrative commentary.)"
        )
    if section == "profitability":
        return (
            f"Gross margin reached {data['gross_margin_pct'][-1]}% in {data['periods'][-1]}, up from "
            f"{data['gross_margin_pct'][0]}%. Operating margin remains negative at {data['operating_margin_pct'][-1]}% "
            "but has improved materially year-on-year. "
            "(Fallback summary — configure GROQ_API_KEY (free) or ANTHROPIC_API_KEY for AI-generated narrative commentary.)"
        )
    if section == "cash":
        return (
            f"Closing cash was \u20ac{data['cash_end'][-1]:,.0f}, implying a modelled runway of "
            f"{data.get('cash_runway_months')} months at the trailing FY2025 burn rate, before accounting for "
            "post year-end financing. "
            "(Fallback summary — configure GROQ_API_KEY (free) or ANTHROPIC_API_KEY for AI-generated narrative commentary.)"
        )
    if section == "solvency":
        return (
            f"DSCR is estimated at {data.get('dscr_status')}. Net assets/liabilities position moved to "
            f"\u20ac{data['net_assets_liabilities'][-1]:,.0f}. "
            "(Fallback summary — configure GROQ_API_KEY (free) or ANTHROPIC_API_KEY for AI-generated narrative commentary.)"
        )
    if section == "returns":
        return (
            f"ROCE status: {data.get('roce_status')}. "
            "(Fallback summary — configure GROQ_API_KEY (free) or ANTHROPIC_API_KEY for AI-generated narrative commentary.)"
        )
    return "No commentary available."


def _call_llm(section: str, data: dict) -> str:
    audience = SECTION_AUDIENCE_HINT.get(section, "the Board")

    system = (
        "You are writing the commentary paragraph that sits above a chart in a board "
        "report for Senus PLC, a Natural Capital management software company listed on "
        "Euronext Access Dublin."
    )
    prompt = f"""This section is for {audience}.

Here is the computed data for this section (already calculated, do not recompute — just interpret it):
{data}

Write 3-4 sentences of tight, board-appropriate commentary. Be specific with numbers. Where the data
includes an assumption_note or similar caveat, weave the key caveat in briefly rather than ignoring it.
Do not use markdown headers or bullet points — plain prose only. Do not repeat the raw JSON back."""

    return chat_json(system, prompt, max_tokens=500).strip()


def _generate(section: str, db: Session, force: bool = False) -> InsightResponse:
    if section not in SECTION_BUILDERS:
        return InsightResponse(
            section=section, content="Unknown section.", model=None,
            is_fallback=True, generated_at=datetime.now(timezone.utc).isoformat(),
        )

    cached = db.query(InsightCache).filter(InsightCache.section == section).first()
    if cached and not force:
        return InsightResponse(
            section=section, content=cached.content, model=cached.model,
            is_fallback=cached.is_fallback, generated_at=cached.generated_at.isoformat(),
        )

    data = SECTION_BUILDERS[section](db)

    try:
        content = _call_llm(section, data)
        is_fallback = False
        model_used = current_model_label()
    except Exception as e:
        # Log the real cause instead of silently falling back — a bad key,
        # network error, or provider outage should be visible in the server
        # logs, not just show up as unexplained fallback text in the UI.
        print(f"[insights] AI commentary call failed for section '{section}' "
              f"({type(e).__name__}): {e}")
        content = _fallback_text(section, data)
        is_fallback = True
        model_used = None

    now = datetime.now(timezone.utc)
    if cached:
        cached.content, cached.model, cached.is_fallback, cached.generated_at = content, model_used, is_fallback, now
    else:
        cached = InsightCache(section=section, content=content, model=model_used, is_fallback=is_fallback, generated_at=now)
        db.add(cached)
    db.commit()

    return InsightResponse(
        section=section, content=content, model=model_used,
        is_fallback=is_fallback, generated_at=now.isoformat(),
    )


@router.get("/{section}", response_model=InsightResponse)
def get_insight(section: str, db: Session = Depends(get_db)):
    return _generate(section, db, force=False)


@router.post("/{section}/generate", response_model=InsightResponse)
def regenerate_insight(section: str, db: Session = Depends(get_db)):
    return _generate(section, db, force=True)