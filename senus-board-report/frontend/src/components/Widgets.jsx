export function fmtEUR(n, opts = {}) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const { compact = false } = opts;
  return new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: compact ? 1 : 0,
    notation: compact ? "compact" : "standard",
  }).format(n);
}

export function fmtPct(n, opts = {}) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const { showSign = false } = opts;
  const sign = showSign && n > 0 ? "+" : "";
  return `${sign}${n}%`;
}

export function KpiCard({ label, value, sub, tone }) {
  const cls = "kpi-value" + (tone ? ` ${tone}` : "");
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className={cls}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

export function ChartCard({ title, sub, children }) {
  return (
    <div className="chart-card">
      <div className="chart-card-title">{title}</div>
      {sub && <div className="chart-card-sub">{sub}</div>}
      {children}
    </div>
  );
}

export function AssumptionNote({ children }) {
  return (
    <div className="assumption-note">
      <strong>Assumption / note: </strong>
      {children}
    </div>
  );
}

export function AiCommentary({ insight, onRegenerate, loading }) {
  if (!insight) return null;
  return (
    <div className="ai-commentary">
      <div className="ai-commentary-label">
        <span className="ai-dot" />
        {insight.is_fallback ? "Summary (AI commentary unavailable)" : `AI commentary — ${insight.model}`}
        {onRegenerate && (
          <button
            className="btn-ghost"
            style={{ marginLeft: "auto" }}
            onClick={onRegenerate}
            disabled={loading}
          >
            {loading ? "Regenerating…" : "Regenerate"}
          </button>
        )}
      </div>
      <p>{insight.content}</p>
    </div>
  );
}

export function Loading() {
  return <div className="loading">Loading board data…</div>;
}

export function ErrorBox({ message }) {
  return (
    <div className="error-box">
      Couldn't load data from the API: {message}. Is the backend running at{" "}
      <code>localhost:8000</code>?
    </div>
  );
}
