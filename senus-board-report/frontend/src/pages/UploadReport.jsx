import { useState, useEffect, useCallback } from "react";
import api from "../api";
import { ChartCard, ErrorBox, fmtEUR } from "../components/Widgets";

const PERIOD_FIELD_LABELS = {
  fiscal_year_end: "Fiscal year end (YYYY-MM-DD)",
  label: "Label (e.g. FY2026 H1)",
  turnover: "Turnover",
  gross_profit: "Gross profit",
  operating_profit: "Operating profit / (loss)",
  profit_before_tax: "Profit / (loss) before tax",
  profit_after_tax: "Profit / (loss) after tax",
  net_assets_liabilities: "Net (liabilities) / assets",
  retained_earnings: "Retained earnings",
  cash_flow_operating: "Cash flow — operating",
  cash_flow_investing: "Cash flow — investing",
  cash_flow_financing: "Cash flow — financing",
  net_change_in_cash: "Net change in cash",
  cash_start: "Cash — start of period",
  cash_end: "Cash — end of period",
  admin_expenses: "Administrative expenses",
  rd_expenditure_pct_revenue: "R&D expenditure (% of revenue)",
  trade_debtors: "Trade debtors",
  trade_creditors: "Trade creditors",
  total_customers: "Total customer accounts",
  enterprise_customers: "Enterprise customers",
  independent_customers: "Independent customers",
  rd_customers: "R&D customers",
  revenue_pct_enterprise: "Revenue % — Enterprise",
  revenue_pct_independent: "Revenue % — Independent",
  revenue_pct_rd: "Revenue % — R&D",
  revenue_pct_ireland: "Revenue % — Ireland",
};

const TEXT_FIELDS = new Set(["fiscal_year_end", "label", "source_note"]);

function emptyExtraction() {
  return { periods: [], product_acv: [], kpi_targets: [], corporate_facts: [] };
}

export default function UploadReport() {
  const [mode, setMode] = useState("idle"); // idle | extracting | review | committing | done
  const [pastedText, setPastedText] = useState("");
  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [extraction, setExtraction] = useState(emptyExtraction());
  const [warnings, setWarnings] = useState([]);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  const loadHistory = useCallback(() => {
    api.listDocuments().then(setHistory).catch(() => {});
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  async function handleExtract() {
    if (!file && !pastedText.trim()) {
      setError("Choose a PDF file or paste the report text first.");
      return;
    }
    setError(null);
    setMode("extracting");
    try {
      const formData = new FormData();
      if (file) formData.append("file", file);
      else formData.append("text", pastedText);

      const res = await api.extractDocument(formData);
      setDocumentId(res.document_id);
      setExtraction(res.extraction);
      setWarnings(res.warnings || []);
      setMode("review");
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setMode("idle");
    } finally {
      loadHistory();
    }
  }

  function updatePeriodField(periodIndex, field, value) {
    setExtraction((prev) => {
      const periods = [...prev.periods];
      const isNumeric = !TEXT_FIELDS.has(field);
      periods[periodIndex] = {
        ...periods[periodIndex],
        [field]: isNumeric ? (value === "" ? null : Number(value)) : value,
      };
      return { ...prev, periods };
    });
  }

  async function handleCommit() {
    setError(null);
    setMode("committing");
    try {
      await api.commitDocument(documentId, extraction);
      setMode("done");
      loadHistory();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setMode("review");
    }
  }

  function handleDiscard() {
    if (documentId) api.discardDocument(documentId).catch(() => {});
    setMode("idle");
    setFile(null);
    setPastedText("");
    setExtraction(emptyExtraction());
    setDocumentId(null);
    loadHistory();
  }

  function startAnother() {
    setMode("idle");
    setFile(null);
    setPastedText("");
    setExtraction(emptyExtraction());
    setDocumentId(null);
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-eyebrow">Board Report</div>
        <h1 className="page-title">Upload Report</h1>
      </div>

      <ChartCard
        title="Add a new filing"
        sub="Upload a PDF or paste the text of a new financial report (e.g. the FY2026 half-year results). AI extracts the figures; you review and confirm before anything is added to the Board Report."
      >
        {mode === "idle" && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: "0.85rem", marginBottom: 6, color: "var(--text-on-paper-muted)" }}>
                PDF file
              </label>
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => { setFile(e.target.files[0] || null); setPastedText(""); }}
              />
            </div>

            <div style={{ margin: "12px 0", color: "var(--text-on-paper-muted)", fontSize: "0.85rem" }}>— or —</div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: "0.85rem", marginBottom: 6, color: "var(--text-on-paper-muted)" }}>
                Paste report text
              </label>
              <textarea
                rows={8}
                style={{ width: "100%", padding: 10, fontFamily: "IBM Plex Mono", fontSize: "0.82rem" }}
                placeholder="Paste the financial summary section here…"
                value={pastedText}
                onChange={(e) => { setPastedText(e.target.value); setFile(null); }}
              />
            </div>

            {error && <ErrorBox message={error} />}

            <button className="btn-primary" style={{ width: "auto", padding: "10px 22px" }} onClick={handleExtract}>
              Extract with AI
            </button>
          </div>
        )}

        {mode === "extracting" && <div className="loading">Extracting figures with Claude…</div>}

        {mode === "review" && (
          <ReviewPanel
            extraction={extraction}
            warnings={warnings}
            error={error}
            onFieldChange={updatePeriodField}
            onCommit={handleCommit}
            onDiscard={handleDiscard}
          />
        )}

        {mode === "committing" && <div className="loading">Saving to the Board Report…</div>}

        {mode === "done" && (
          <div>
            <p style={{ marginBottom: 16 }}>
              Saved. The new period now appears across Overview, Growth & Revenue, and every
              other section — charts and YoY comparisons update automatically.
            </p>
            <button className="btn-ghost" onClick={startAnother}>Upload another report</button>
          </div>
        )}
      </ChartCard>

      <ChartCard title="Upload history" sub="Every filing run through the extraction pipeline, and whether it was committed to the Board Report.">
        {history.length === 0 ? (
          <p style={{ color: "var(--text-on-paper-muted)", fontSize: "0.88rem" }}>No uploads yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>File</th><th>Period</th><th>Status</th><th>Uploaded</th></tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{h.filename || "(pasted text)"}</td>
                  <td>{h.fiscal_year_end || "—"}</td>
                  <td>{h.status}</td>
                  <td>{new Date(h.uploaded_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ChartCard>
    </div>
  );
}

function ReviewPanel({ extraction, warnings, error, onFieldChange, onCommit, onDiscard }) {
  if (extraction.periods.length === 0) {
    return (
      <div>
        {warnings.map((w, i) => <ErrorBox key={i} message={w} />)}
        <div style={{ marginTop: 16 }}>
          <button className="btn-ghost" onClick={onDiscard}>Start over</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {warnings.map((w, i) => <ErrorBox key={i} message={w} />)}
      <p style={{ fontSize: "0.85rem", color: "var(--text-on-paper-muted)", marginBottom: 16 }}>
        Review the figures Claude extracted below. Correct anything that looks wrong before
        confirming — nothing is written to the Board Report until you commit.
      </p>

      {extraction.periods.map((period, pIndex) => (
        <div key={pIndex} style={{ marginBottom: 24 }}>
          <div className="chart-card-title" style={{ marginBottom: 12 }}>
            {period.label || `Period ${pIndex + 1}`}
          </div>
          <table className="table">
            <tbody>
              {Object.entries(PERIOD_FIELD_LABELS).map(([field, fieldLabel]) => (
                <tr key={field}>
                  <td style={{ width: "45%" }}>{fieldLabel}</td>
                  <td>
                    <input
                      type={TEXT_FIELDS.has(field) ? "text" : "number"}
                      value={period[field] ?? ""}
                      onChange={(e) => onFieldChange(pIndex, field, e.target.value)}
                      style={{
                        width: "100%",
                        padding: "6px 8px",
                        fontFamily: TEXT_FIELDS.has(field) ? "IBM Plex Sans" : "IBM Plex Mono",
                        fontSize: "0.85rem",
                        border: "1px solid var(--paper-line)",
                        borderRadius: 3,
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {period.source_note && (
            <div className="assumption-note" style={{ marginTop: 10 }}>
              <strong>AI note: </strong>{period.source_note}
            </div>
          )}
        </div>
      ))}

      {error && <ErrorBox message={error} />}

      <div style={{ display: "flex", gap: 12 }}>
        <button className="btn-primary" style={{ width: "auto", padding: "10px 22px" }} onClick={onCommit}>
          Confirm & add to Board Report
        </button>
        <button className="btn-ghost" onClick={onDiscard}>Discard</button>
      </div>
    </div>
  );
}