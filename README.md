# Senus PLC — Board Report

An AI-native full-stack platform that turns Senus PLC's public financial disclosures
(Euronext Access Information Document, December 2025) into an interactive board report
for Management, the Board, Equity Investors, and Credit Providers.

Built for the Assiduous Technology Graduate Assessment.


---

## 1. What it does

Six report sections, matching the brief:

| Section | Metrics |
|---|---|
| **Overview** | Primary KPI (revenue vs. Senus 2030 CAGR target), cross-section snapshot, company facts |
| **Growth & Revenue** | Revenue YoY, revenue by channel (Enterprise / Independent / R&D), geographic mix, customer counts, Average Contract Value by product |
| **Profitability** | Gross / operating / EBITDA (proxy) / net margin, cost breakdown |
| **Cash & Liquidity** | Cash position, monthly burn, modelled cash runway, trade working capital, EBITDA-to-Free-Cash-Flow bridge |
| **Solvency & Leverage** | Net assets/(liabilities), illustrative Debt Service Coverage Ratio, gearing commentary |
| **Returns** | ROCE assessment (with disclosed-data limitations explained), Average Contract Value vs. FY2030 target |

Every section carries an **AI-generated commentary** paragraph (a real Claude API call,
with a templated fallback if no API key is configured) and, where a metric relies on
an assumption not explicitly disclosed in the source document, a visible **assumption note**.

---

## 2. Architecture

```
                 ┌─────────────────────────┐
  Information    │   app/ai_extraction.py  │   real Anthropic API call
  Document text  │   (LLM extraction)      │───┐  parses raw text → JSON,
  ──────────────▶│                         │   │  validated by Pydantic
                 └─────────────────────────┘   ▼
                                    app/data/extracted_financials.json
                                                │
                                                ▼
                                        app/seed.py
                                     (loads JSON → SQLite)
                                                │
                                                ▼
                    ┌───────────────────────────────────────────┐
                    │              FastAPI backend               │
                    │  models.py    SQLAlchemy ORM (SQLite)       │
                    │  metrics.py   derived-metric calculators    │
                    │                 (growth, margins, DSCR,     │
                    │                  runway, ROCE, FCF bridge)  │
                    │  routers/financials.py   /api/financials/*  │
                    │  routers/insights.py     /api/insights/*    │
                    │                 (Claude commentary, cached) │
                    └───────────────────────────────────────────┘
                                                │  REST / JSON
                                                ▼
                    ┌───────────────────────────────────────────┐
                    │              React frontend                 │
                    │  Vite + React Router + Recharts + Axios     │
                    │  pages/*.jsx  one page per report section   │
                    │  Login → Layout(sidebar) → section pages    │
                    └───────────────────────────────────────────┘
```

**Why this split:**
- **Extraction is separated from serving.** The LLM is only used once, offline, to turn
  messy source text into a validated structured record — not called on every page load
  for basic figures. This keeps the dashboard fast, cheap, and reproducible, and means a
  bad extraction run can be inspected and re-run without touching the API or UI.
- **Metrics are computed server-side, in one place** (`app/metrics.py`), not duplicated
  in the frontend. Every derived figure (EBITDA proxy, DSCR, cash runway, ROCE) has a
  single source of truth, and every assumption behind it lives next to the calculation
  and is returned to the client as an explicit `assumption_note` / `dscr_note` / etc.
  field — the UI is required to surface these, not just the numbers.
- **AI commentary is a distinct, cached layer** (`InsightCache` table) rather than baked
  into the metrics endpoints, so regenerating a board narrative doesn't require
  recomputing figures, and a missing API key degrades to a clearly labelled fallback
  instead of breaking the page.

---

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite | Fast to build, typed request/response models via Pydantic, zero-ops database appropriate for this dataset's scale |
| AI extraction & insights | Anthropic API (`claude-sonnet-4-6`) | Real API calls, not mocked — see §4 |
| Frontend | React (Vite) + React Router + Recharts + Axios | Modern, fast dev loop; Recharts gives production-quality financial charts with minimal code |
| Auth | Lightweight client-side session (mock) | The brief asks for a platform "a CEO would log in to and use" — a full IdP/SSO integration was out of scope for the assessment window; this is called out explicitly as a placeholder in `Login.jsx` and below |

---

## 4. AI-assisted development workflow

1. **Source gathering**: fetched the Senus PLC Euronext Information Document (the
   primary reference on the investor relations site) and extracted the "Operating and
   Financial Review" and KPI sections as raw text (`backend/app/data/source_document.txt`).
2. **AI extraction** (`backend/app/ai_extraction.py`): calls the Anthropic Messages API
   with that raw text and a target Pydantic schema (`ExtractionResult` in `schemas.py`),
   instructing the model to extract only explicitly disclosed figures, flag anything it
   had to lightly derive (e.g. FY2024 admin expenses, which is only stated as "FY2025 is
   an 18% decrease of €274,795"), and never invent numbers. The model's JSON response is
   validated against the Pydantic schema before being trusted — if it doesn't validate,
   the script raises rather than silently seeding bad data.
   Run it yourself with:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   cd backend && python -m app.ai_extraction
   ```
   The validated output of an actual run is committed at
   `backend/app/data/extracted_financials.json` so the app runs out of the box without
   requiring a key just to see the dashboard.
3. **Seeding** (`backend/app/seed.py`): loads that validated JSON into SQLite.
4. **AI board commentary** (`backend/app/routers/insights.py`): for each section, the
   *already-computed* metrics (not raw text) are sent to Claude with a short prompt asking
   for board-appropriate prose that references the real numbers and weaves in the
   relevant caveat. This is a live API call at request time (cached in `InsightCache`
   so it isn't re-run on every page view); `POST /api/insights/{section}/generate` forces
   a regeneration. Without a key, a clearly labelled templated fallback is used instead
   — the app never breaks or shows fabricated commentary as if it were AI-generated.
5. **This README, the metric formulas, and the frontend** were built iteratively with
   an AI pair-programming workflow (Claude, via this same assessment session):
   scaffolding the FastAPI/SQLAlchemy layer, deriving the metric calculations from the
   source figures, and building the React dashboard.

---

## 5. Assumptions made (and how they're surfaced)

The source Information Document is an investor-relations document, not a full statutory
account, so several requested board metrics require assumptions. Each is computed in
`backend/app/metrics.py`, returned by the API as an explicit note field, and rendered in
the UI as a visible callout — never silently baked into a number.

| Metric | Assumption | Where it's shown |
|---|---|---|
| **EBITDA / EBITDA margin** | No D&A line is disclosed. Investing cash outflows are minimal (€3.5k FY2025, €33.5k FY2024), consistent with an asset-light software business, so EBITDA is approximated as Operating Profit. | `assumption_note` on Profitability |
| **Cash runway** | Modelled as closing cash ÷ average FY2025 monthly operating cash burn. This is a trailing, operations-only view — it excludes the €1.1m Private Placement (Dec 2025) and €100k SBCI loan, both of which materially improve actual liquidity post year-end. | `assumption_note` on Cash & Liquidity |
| **DSCR (Debt Service Coverage Ratio)** | The €100,000 SBCI-backed term loan's actual rate/term isn't disclosed. An illustrative 5-year amortising structure at 6% p.a. is assumed to estimate annual debt service (~€23.7k/yr) purely to give credit providers a directional read. | `dscr_note` on Solvency & Leverage |
| **ROCE** | Computed as Operating Profit ÷ estimated Capital Employed (Net Assets/(Liabilities) + Non-current Liabilities). The source document discloses equity directly but only the *movement* in non-current liabilities (+€83,655 in FY2025, following the new loan drawdown), not the absolute balance — so FY2024 non-current liabilities are assumed negligible and FY2025's is assumed to equal that disclosed movement. Result: −196.8% (FY2024), −930.8% (FY2025) — directionally robust (deeply negative, driven by both operating losses and a very small capital base), magnitude is an estimate. | `roce_note` on Returns |
| **Month-over-month revenue growth** | Not computable — the source document discloses annual (FY-end) figures only, 365 days apart. Rather than omit the metric silently, the calculator checks the actual gap between the two most recent stored periods and computes real MoM growth automatically once monthly management accounts are uploaded via "Upload Report" — no code change needed then. | `mom_note` on Growth & Revenue |
| **Bookings** | Not disclosed anywhere in the source document — only recognised revenue and Enterprise ACV by product are given. The Company describes tracking a sales funnel (leads, prospects, priced, won) internally, which would be the real source for this metric, but that requires a CRM/pipeline connector, not a financial filing. | `bookings_note` on Growth & Revenue |
| **FY2024 customer/channel breakdown** | Not disclosed in the source document (only FY2025's 36/98/4 Enterprise/Independent/R&D split and 138 total accounts are given) — left as `null` rather than estimated, and the UI renders "—". | Growth & Revenue |
| **FY2024 geographic mix** | Only "<5% of revenue from outside Ireland" is disclosed for FY2024 (vs. an exact 78%/22% split for FY2025); the app derives ~95%/5% as an approximation and labels the chart accordingly. | Growth & Revenue chart caption |
| **Authentication** | Mocked client-side session (any email/password) rather than real SSO/IdP — out of scope for the assessment, called out on the login screen itself. | `Login.jsx` |

---

## 6. How outputs were validated

- **Backend, end-to-end, via live requests** — not just unit assertions. The FastAPI
  server was run locally and every endpoint hit with `curl` against the seeded database:
  `/api/health`, `/api/financials/{periods,corporate-facts,kpi-targets,growth,
  profitability,cash-liquidity,solvency,returns}`, and `/api/insights/{section}` in both
  its AI-call and no-key-fallback paths. Response shapes and values were checked by hand
  against the source Information Document figures (e.g. confirmed FY2025 revenue YoY
  growth computes to 21.6%, matching the Directors' own stated figure in the narrative
  text, as an independent cross-check on the metrics engine rather than trusting the
  extraction alone).
- **Extraction validation is structural, not just eyeballed**: the LLM's JSON output is
  parsed into the same Pydantic `ExtractionResult` model used to define the schema it was
  asked to produce, so a malformed or incomplete extraction fails loudly (`ValidationError`)
  rather than silently seeding partial data.
- **Frontend**: `npm run build` (production Vite build) passes with zero errors. Every
  field referenced in each page component (`data.gross_margin_pct`, `data.dscr_status`,
  etc.) was cross-checked line-by-line against the actual JSON returned by the live
  backend endpoints (captured during the curl testing above), not assumed from the
  schema alone.
- **Numerical sanity checks performed by hand**: gross margin FY2025 = €648,450 /
  €836,991 = 77.5% (matches the Directors' stated 77.5% exactly); revenue growth =
  (€836,991 − €688,317) / €688,317 = 21.6% (matches the Directors' stated 21.6% exactly).
  These two independent confirmations against the source document's own narrative text
  gave confidence in both the extraction step and the metrics engine.

---

## 7. Running it locally

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # loads the committed extraction output into SQLite
uvicorn app.main:app --reload --port 8000
```
Optional — to re-run live AI extraction / enable live AI commentary:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m app.ai_extraction   # regenerates extracted_financials.json, then re-run seed
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```
The frontend expects the API at `http://localhost:8000` (see `frontend/.env`,
`VITE_API_BASE`).

Sign in with any email/password (mock auth) to view the dashboard.

---

## 8. Deployment

Deployed on [Render](https://render.com) — free tier, no credit card required,
deploys straight from this GitHub repo.

- **Live app:** _add your Render URL here_

### One-time setup

1. **Push this repo to GitHub** if you haven't already (see repo root for git history).
2. **Get a free Groq key** (or Anthropic key) — see §4 above — you'll need it in step 4.
3. **Create the backend service:**
   - Render dashboard → **New** → **Web Service** → connect this repo
   - Root directory: leave blank (repo root) · Runtime: **Docker**
   - Dockerfile path: `backend/Dockerfile` · Docker context: `backend`
   - Plan: **Free**
   - Deploy. Once live, note its URL — something like `https://senus-board-report-api.onrender.com`
4. **Set the backend's environment variables** (dashboard → service → Environment):
   - `GROQ_API_KEY` = your key (or `ANTHROPIC_API_KEY`)
   - Leave `ALLOWED_ORIGINS` for now — comes back in step 6
5. **Create the frontend service:**
   - Render dashboard → **New** → **Static Site** → same repo
   - Build command: `cd frontend && npm install && npm run build`
   - Publish directory: `frontend/dist`
   - Add environment variable **`VITE_API_BASE`** = the backend URL from step 3 (this is a *build-time* variable — Vite bakes it into the static bundle, so it must be set before the build runs, not after)
   - Deploy. Note its URL — something like `https://senus-board-report-ui.onrender.com`
6. **Close the loop — set CORS on the backend:**
   - Back on the backend service's Environment tab, set `ALLOWED_ORIGINS` = the frontend URL from step 5 (e.g. `https://senus-board-report-ui.onrender.com`)
   - This triggers a redeploy automatically; without this step the deployed frontend can reach the API but every request fails with a CORS error
7. Visit the frontend URL, sign in (mock auth, any email/password), confirm the dashboard loads real data.

A `render.yaml` Blueprint is included at the repo root as a shortcut for steps 3 and 5 (Render dashboard → **New** → **Blueprint**) — it still requires the manual env var wiring in steps 4 and 6 above, since Render can't know either URL before both services exist.

### Known limitations of the free tier (documented, not hidden)

- **Free web services spin down after 15 minutes of inactivity** and take ~30-60s to wake on the next request — the first load after idle time will be slow. This is a free-tier constraint, not an application bug.
- **The SQLite database resets on redeploy** (a genuine `git push` → new build), but persists across normal idle spin-down/wake cycles. `backend/entrypoint.sh` is written to be idempotent — it only re-seeds from the committed extraction JSON if no database file exists yet, specifically so that reports uploaded live via "Upload Report" survive ordinary sleep/wake cycles and are only lost on an actual redeploy.
- For a production deployment handling real uploads over time, the next step would be swapping SQLite for Render's managed Postgres (small free tier, 1GB, 30-day expiry) so data survives redeploys too — noted in §9 below.

## 9. What I'd build next with more time

- Swap SQLite for Render's managed Postgres, so live-uploaded data survives a redeploy, not just idle spin-down/wake cycles.


- Real balance-sheet ingestion (once full statutory accounts are available) to compute
  a precise ROCE and gearing ratio instead of the documented approximations.
- Replace mock auth with real SSO.
- Break the frontend bundle into route-based chunks (Recharts pushes the current single
  bundle to ~715kB) via `React.lazy`.
- A scenario/forecast layer projecting the Senus 2030 50% CAGR target forward against
  actuals, for the Board's trading-update meetings.
