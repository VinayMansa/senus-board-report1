import { BarChart, Bar, ComposedChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, ReferenceLine } from "recharts";
import api from "../api";
import { useSection } from "../hooks/useSection";
import { KpiCard, ChartCard, AssumptionNote, AiCommentary, Loading, ErrorBox, fmtEUR } from "../components/Widgets";

export default function CashLiquidity() {
  const { data, insight, loading, insightLoading, error, regenerate } = useSection(api.cashLiquidity, "cash");

  if (error) return <ErrorBox message={error} />;
  if (loading || !data) return <Loading />;

  const cashTrend = data.periods.map((p, i) => ({
    period: p,
    "Cash at year end": data.cash_end[i],
    "Operating cash flow": data.operating_cash_flow[i],
  }));

  const wcTrend = data.periods.map((p, i) => ({
    period: p,
    "Trade working capital": data.trade_working_capital[i],
  }));

  const latestPeriod = data.periods[data.periods.length - 1];
  const bridge = data.ebitda_to_fcf_bridge[latestPeriod] || {};
  const bridgeRows = Object.entries(bridge);

  return (
    <div>
      <div className="page-header">
        <div className="page-eyebrow">Board Report</div>
        <h1 className="page-title">Cash & Liquidity</h1>
      </div>

      <AiCommentary insight={insight} onRegenerate={regenerate} loading={insightLoading} />

      <div className="kpi-row">
        <KpiCard label="Closing cash (FY2025)" value={fmtEUR(data.cash_end[data.cash_end.length - 1])} sub={`vs. ${fmtEUR(data.cash_end[0])} FY2024`} />
        <KpiCard label="Monthly cash burn" value={fmtEUR(data.monthly_cash_burn)} sub="avg. FY2025 operating outflow" tone="negative" />
        <KpiCard label="Modelled cash runway" value={`${data.cash_runway_months} mo.`} sub="at trailing burn rate — see note" tone="negative" />
        <KpiCard label="Trade working capital (FY2025)" value={fmtEUR(data.trade_working_capital[data.trade_working_capital.length - 1])} sub="debtors less creditors" />
      </div>

      <AssumptionNote>{data.assumption_note}</AssumptionNote>

      <div style={{ height: 20 }} />

      <div className="chart-grid">
        <ChartCard title="Cash position" sub="Closing cash vs. operating cash flow, FY2024–FY2025 (€)">
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={cashTrend}>
              <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" />
              <XAxis dataKey="period" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={{ stroke: "#d8ceb4" }} tickLine={false} />
              <YAxis tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => fmtEUR(v)} />
              <Legend />
              <ReferenceLine y={0} stroke="#d8ceb4" />
              <Bar dataKey="Cash at year end" fill="#c99a3e" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Operating cash flow" fill="#ab4a35" radius={[2, 2, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Trade working capital" sub="Trade debtors less trade creditors (€)">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={wcTrend}>
              <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={{ stroke: "#d8ceb4" }} tickLine={false} />
              <YAxis tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => fmtEUR(v)} />
              <Bar dataKey="Trade working capital" fill="#3e8e82" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <ChartCard title={`EBITDA-to-Free-Cash-Flow bridge, ${latestPeriod}`} sub="EBITDA (proxy) → working capital & other movements → operating cash flow → capex → free cash flow">
        <table className="table">
          <tbody>
            {bridgeRows.map(([label, value]) => (
              <tr key={label}>
                <td>{label}</td>
                <td className="num">{fmtEUR(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ChartCard>
    </div>
  );
}
