"""
AI-powered financial data extraction pipeline.

Reads the raw text extracted from Senus PLC's public Information Document
(app/data/source_document.txt) and uses the Anthropic API (Claude) to parse
it into the structured schema defined in app/schemas.py::ExtractionResult.
The validated result is written to app/data/extracted_financials.json, which
app/seed.py then loads into the SQLite database.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
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
"""

import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from pydantic import ValidationError

from .schemas import ExtractionResult

APP_DIR = Path(__file__).parent
SOURCE_DOC_PATH = APP_DIR / "data" / "source_document.txt"
OUTPUT_PATH = APP_DIR / "data" / "extracted_financials.json"

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a financial data extraction engine for a board-reporting platform.
You will be given raw text extracted from a public company Information Document.
Your job is to extract EVERY explicitly disclosed financial figure, KPI, and corporate fact
into a single JSON object that strictly matches the schema you are given. Do not invent
numbers. Where a figure is not disclosed in the source text, omit the optional field
(leave it null) rather than guessing. Where you must lightly derive a figure that is
implied but not stated verbatim (e.g. converting a percentage change into an absolute
value already given elsewhere in the text), you may do so, but note it in source_note.
Respond with ONLY the JSON object. No markdown fences, no preamble, no commentary."""


def build_user_prompt(source_text: str, schema_json: dict) -> str:
    return f"""SOURCE DOCUMENT TEXT:
---
{source_text}
---

TARGET JSON SCHEMA (JSON Schema draft, for your reference only — respond with an
instance matching ExtractionResult, not the schema itself):
{json.dumps(schema_json, indent=2)}

Extract two FinancialPeriod entries (FY ended 30 June 2025 and FY ended 30 June 2024),
the ProductACV entries for Senus SOIL / Senus ERA / Senus TERRAIN (FY2025 only, since
that's what's disclosed), the KpiTarget entries from the Senus 2030 strategy KPIs
described in the text, and CorporateFact entries for capital-structure / headcount /
listing facts mentioned in the text.

Return ONLY the JSON object matching ExtractionResult."""


def call_claude(source_text: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Export it before running the extraction "
            "pipeline, e.g.:\n  export ANTHROPIC_API_KEY=sk-ant-...\n  python -m app.ai_extraction"
        )

    client = Anthropic(api_key=api_key)
    schema_json = ExtractionResult.model_json_schema()

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(source_text, schema_json)}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text")
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    return json.loads(raw_text)


def run_extraction() -> ExtractionResult:
    if not SOURCE_DOC_PATH.exists():
        raise FileNotFoundError(f"Source document not found at {SOURCE_DOC_PATH}")

    source_text = SOURCE_DOC_PATH.read_text(encoding="utf-8")
    print(f"[ai_extraction] Read {len(source_text)} chars from {SOURCE_DOC_PATH.name}")
    print(f"[ai_extraction] Calling {MODEL} to extract structured financials...")

    raw_json = call_claude(source_text)

    try:
        result = ExtractionResult.model_validate(raw_json)
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
