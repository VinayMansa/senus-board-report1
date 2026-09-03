"""
AI-powered financial data extraction pipeline.

Reads the raw text extracted from Senus PLC's public Information Document
(app/data/source_document.txt) and uses an LLM (Groq's free tier by default,
or Anthropic Claude if configured — see app/llm_client.py) to parse it into
the structured schema defined in app/schemas.py::ExtractionResult. The
validated result is written to app/data/extracted_financials.json, which
app/seed.py then loads into the SQLite database.

Run:
    export GROQ_API_KEY=gsk_...        # free — console.groq.com/keys
    # or: export ANTHROPIC_API_KEY=sk-ant-...
    python -m app.ai_extraction

Design notes
------------
- We do NOT hand-roll regex/string parsing of the financial tables. The
  source document mixes a formatted summary table with narrative prose
  (e.g. "gross margin expanded to 77.5% from 62.8%"), and a general-purpose
  LLM is far more robust at reconciling the two, catching sign conventions
  ((633,694) = negative), and flagging what is NOT disclosed (e.g. no
  separate D&A line) than brittle pattern matching would be.
- The model is instructed to return ONLY JSON matching ExtractionResult,
  and every field is validated with Pydantic before being trusted. If
  validation fails, the script raises rather than silently seeding bad data.
- Numbers the model infers or estimates (as opposed to figures explicitly
  stated in the source) must be flagged via `source_note`, so downstream
  consumers (the metrics engine, the UI) can visibly mark them as
  assumptions rather than presenting them as disclosed facts.
- The LLM provider is pluggable (app/llm_client.py) — Groq's free, no-card
  tier and Anthropic's paid API are interchangeable here with zero changes
  to this file, selected automatically by which API key is set.
"""

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .llm_client import chat_json, current_model_label
from .schemas import ExtractionResult

APP_DIR = Path(__file__).parent
SOURCE_DOC_PATH = APP_DIR / "data" / "source_document.txt"
OUTPUT_PATH = APP_DIR / "data" / "extracted_financials.json"

SYSTEM_PROMPT = """You are a financial data extraction engine for a board-reporting platform.
You will be given raw text extracted from a public company Information Document.
Your job is to extract EVERY explicitly disclosed financial figure, KPI, and corporate fact
into a single JSON object that strictly matches the schema you are given. Do not invent
numbers. Where a figure is not disclosed in the source text, omit the optional field
(leave it null) rather than guessing. Where you must lightly derive a figure that is
implied but not stated verbatim (e.g. converting a percentage change into an absolute
value already given elsewhere in the text), you may do so, but note it in source_note.
Respond with ONLY the JSON object. No markdown fences, no preamble, no commentary."""


def call_llm(source_text: str, incremental: bool = False) -> dict:
    """Calls the configured LLM provider (see app/llm_client.py) to extract
    structured financials from arbitrary source text. Used both by the
    offline CLI pipeline (full Information Document, `incremental=False`)
    and by the live document-upload endpoint (a single new filing — e.g. a
    half-year report — `incremental=True`, which relaxes the "extract two
    periods" instruction since a fresh filing may only disclose one new
    period)."""

    schema_json = ExtractionResult.model_json_schema()

    if incremental:
        instruction = """Extract whatever FinancialPeriod(s), ProductACV rows, KpiTarget updates,
and CorporateFact updates are disclosed in THIS document — it may be a single half-year
or full-year filing covering just one new period, not necessarily two. Only include a
FinancialPeriod entry for a period that is actually disclosed in this text. Leave
kpi_targets and corporate_facts as empty lists unless this specific document updates them."""
    else:
        instruction = """Extract two FinancialPeriod entries (FY ended 30 June 2025 and FY ended
30 June 2024), the ProductACV entries for Senus SOIL / Senus ERA / Senus TERRAIN (FY2025
only, since that's what's disclosed), the KpiTarget entries from the Senus 2030 strategy
KPIs described in the text, and CorporateFact entries for capital-structure / headcount /
listing facts mentioned in the text."""

    prompt = f"""SOURCE DOCUMENT TEXT:
---
{source_text}
---

TARGET JSON SCHEMA (JSON Schema draft, for your reference only — respond with an
instance matching ExtractionResult, not the schema itself):
{json.dumps(schema_json, indent=2)}

{instruction}

Return ONLY the JSON object matching ExtractionResult."""

    raw_text = chat_json(SYSTEM_PROMPT, prompt, max_tokens=4000).strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    return json.loads(raw_text)


def extract_from_text(source_text: str, incremental: bool = True) -> ExtractionResult:
    """Reusable entry point: run AI extraction on arbitrary text and return a
    validated ExtractionResult. Raises ValidationError if the model's output
    doesn't match the schema — callers should surface that as a 502 to the
    client rather than silently trusting malformed data."""
    raw_json = call_llm(source_text, incremental=incremental)
    return ExtractionResult.model_validate(raw_json)


def run_extraction() -> ExtractionResult:
    """CLI entry point: runs the full offline extraction against the
    committed Information Document text and overwrites extracted_financials.json.
    This is the original bootstrap pipeline — for live, in-app document
    uploads see routers/documents.py, which calls extract_from_text() directly
    and routes through a review step before anything is written to the DB."""
    if not SOURCE_DOC_PATH.exists():
        raise FileNotFoundError(f"Source document not found at {SOURCE_DOC_PATH}")

    source_text = SOURCE_DOC_PATH.read_text(encoding="utf-8")
    print(f"[ai_extraction] Read {len(source_text)} chars from {SOURCE_DOC_PATH.name}")
    print(f"[ai_extraction] Calling {current_model_label()} to extract structured financials...")

    try:
        result = extract_from_text(source_text, incremental=False)
    except ValidationError as e:
        print("[ai_extraction] VALIDATION FAILED — model output did not match schema:")
        print(e)
        raise

    OUTPUT_PATH.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"[ai_extraction] Wrote validated extraction to {OUTPUT_PATH.name}")
    print(f"[ai_extraction]   -> {len(result.periods)} periods, "
          f"{len(result.product_acv)} product ACV rows, "
          f"{len(result.kpi_targets)} KPI targets, "
          f"{len(result.corporate_facts)} corporate facts")
    return result


if __name__ == "__main__":
    try:
        run_extraction()
    except Exception as exc:
        print(f"[ai_extraction] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)