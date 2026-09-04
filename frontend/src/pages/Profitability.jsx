import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import api from "../api";
import { useSection } from "../hooks/useSection";
import { KpiCard, ChartCard, AssumptionNote, AiCommentary, Loading, ErrorBox, fmtEUR, fmtPct } from "../components/Widgets";

export default function Profitability() {
  const { data, insight, loading, insightLoading, error, regenerate } = useSection(api.profitability, "profitability");

  if (error) return <ErrorBox message={error} />;
  if (loading || !data) return <Loading />;

  const marginTrend = data.periods.map((p, i) => ({
    period: p,
    "Gross margin %": data.gross_margin_pct[i],
    "Operating margin %": data.operating_margin_pct[i],
    "Net margin %": data.net_margin_pct[i],
  }));

  const latestPeriod = data.periods[data.periods.length - 1];
  const costRows = Object.entries(data.cost_breakdown[latestPeriod] || {});
  const costChartData = costRows.map(([name, value]) => ({ name, value }));

  return (
    <div>
      <div className="page-header">
        <div className="page-eyebrow">Board Report</div>
        <h1 className="page-title">Profitability</h1>
      </div>

      <AiCommentary insight={insight} onRegenerate={regenerate} loading={insightLoading} />

      <div className="kpi-row">
        <KpiCard label="Gross margin (FY2025)" value={fmtPct(data.gross_margin_pct[1])} sub={`vs. ${fmtPct(data.gross_margin_pct[0])} FY2024`} tone="positive" />
        <KpiCard label="Operating margin (FY2025)" value={fmtPct(data.operating_margin_pct[1])} sub={`vs. ${fmtPct(data.operating_margin_pct[0])} FY2024`} tone="negative" />
        <KpiCard label="EBITDA margin (proxy, FY2025)" value={fmtPct(data.ebitda_margin_pct[1])} tone="negative" />
        <KpiCard label="Net margin (FY2025)" value={fmtPct(data.net_margin_pct[1])} tone="negative" />
      </div>

      <AssumptionNote>{data.assumption_note}</AssumptionNote>

      <div style={{ height: 20 }} />

      <ChartCard title="Margin trend" sub="Gross / operating / net margin, FY2024–FY2025 (%)">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={marginTrend}>
            <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" />
            <XAxis dataKey="period" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={{ stroke: "#d8ceb4" }} tickLine={false} />
            <YAxis tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
            <Tooltip formatter={(v) => `${v}%`} />
            <Legend />
            <Line type="monotone" dataKey="Gross margin %" stroke="#6f8c4d" strokeWidth={2.5} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="Operating margin %" stroke="#c99a3e" strokeWidth={2.5} dot={{ r: 4 }} />
            <Line type="monotone" dataKey="Net margin %" stroke="#ab4a35" strokeWidth={2.5} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title={`Cost breakdown, ${latestPeriod}`} sub="Cost of sales vs. administrative expenses (€)">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={costChartData} layout="vertical">
            <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`} />
            <YAxis type="category" dataKey="name" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} width={160} />
            <Tooltip formatter={(v) => fmtEUR(v)} />
            <Bar dataKey="value" fill="#3e8e82" radius={[0, 2, 2, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
