import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";
import api from "../api";
import { useSection } from "../hooks/useSection";
import { KpiCard, ChartCard, AssumptionNote, AiCommentary, Loading, ErrorBox, fmtEUR } from "../components/Widgets";

export default function SolvencyLeverage() {
  const { data, insight, loading, insightLoading, error, regenerate } = useSection(api.solvency, "solvency");

  if (error) return <ErrorBox message={error} />;
  if (loading || !data) return <Loading />;

  const equityTrend = data.periods.map((p, i) => ({
    period: p,
    "Net assets / (liabilities)": data.net_assets_liabilities[i],
  }));

  return (
    <div>
      <div className="page-header">
        <div className="page-eyebrow">Board Report</div>
        <h1 className="page-title">Solvency & Leverage</h1>
      </div>

      <AiCommentary insight={insight} onRegenerate={regenerate} loading={insightLoading} />

      <div className="kpi-row">
        <KpiCard
          label="Net assets / (liabilities), FY2025"
          value={fmtEUR(data.net_assets_liabilities[data.net_assets_liabilities.length - 1])}
          sub={`vs. ${fmtEUR(data.net_assets_liabilities[0])} FY2024`}
          tone="negative"
        />
        <KpiCard label="New debt drawn (FY2025)" value={fmtEUR(data.new_debt_drawn)} sub="SBCI-backed term loan" />
        <KpiCard label="Debt Service Coverage Ratio" value={data.dscr_status} sub="illustrative — see note" tone="negative" />
      </div>

      <AssumptionNote>{data.dscr_note}</AssumptionNote>
      <div style={{ height: 12 }} />
      <AssumptionNote>{data.gearing_note}</AssumptionNote>

      <div style={{ height: 20 }} />

      <ChartCard title="Net assets / (liabilities)" sub="FY2024–FY2025 (€) — the Company had negative shareholders' equity at 30 June 2025">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={equityTrend}>
            <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="period" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={{ stroke: "#d8ceb4" }} tickLine={false} />
            <YAxis tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`} />
            <Tooltip formatter={(v) => fmtEUR(v)} />
            <ReferenceLine y={0} stroke="#1c2417" />
            <Bar dataKey="Net assets / (liabilities)" radius={[2, 2, 0, 0]}>
              {equityTrend.map((entry, i) => (
                <Cell key={i} fill={entry["Net assets / (liabilities)"] >= 0 ? "#6f8c4d" : "#ab4a35"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
