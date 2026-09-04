import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import api from "../api";
import { useSection } from "../hooks/useSection";
import { KpiCard, ChartCard, AssumptionNote, AiCommentary, Loading, ErrorBox, fmtEUR, fmtPct } from "../components/Widgets";

const CHANNEL_COLORS = ["#c99a3e", "#3e8e82", "#6f8c4d"];

export default function GrowthRevenue() {
  const { data, insight, loading, insightLoading, error, regenerate } = useSection(api.growth, "growth");

  if (error) return <ErrorBox message={error} />;
  if (loading || !data) return <Loading />;

  const revenueByYear = data.periods.map((p, i) => ({ period: p, revenue: data.revenue[i] }));

  const latestChannelYear = Object.keys(data.revenue_by_channel).sort().pop();
  const channelData = latestChannelYear
    ? Object.entries(data.revenue_by_channel[latestChannelYear]).map(([name, value]) => ({ name, value }))
    : [];

  const geoYears = Object.keys(data.revenue_by_geography).sort();
  const geoData = geoYears.map((y) => ({
    period: y,
    Ireland: data.revenue_by_geography[y].Ireland,
    "Outside Ireland": data.revenue_by_geography[y]["Outside Ireland"],
  }));

  return (
    <div>
      <div className="page-header">
        <div className="page-eyebrow">Board Report</div>
        <h1 className="page-title">Growth & Revenue</h1>
      </div>

      <AiCommentary insight={insight} onRegenerate={regenerate} loading={insightLoading} />

      <div className="kpi-row">
        <KpiCard label="FY2025 revenue" value={fmtEUR(data.revenue[data.revenue.length - 1])} />
        <KpiCard
          label="YoY growth"
          value={fmtPct(data.revenue_yoy_growth_pct, { showSign: true })}
          sub={`vs. ${data.cagr_target_pct}% CAGR target`}
          tone="positive"
        />
        <KpiCard label="Total customer accounts" value={data.customers_total[data.customers_total.length - 1] ?? "—"} sub="FY2025" />
        <KpiCard
          label="Ireland share of revenue"
          value={fmtPct(data.revenue_by_geography[geoYears[geoYears.length - 1]]?.Ireland)}
          sub="target: <50% by FY2030"
        />
        <KpiCard
          label="Month-over-month growth"
          value={data.mom_revenue_growth_pct !== null ? fmtPct(data.mom_revenue_growth_pct, { showSign: true }) : "—"}
          sub={data.mom_revenue_growth_pct !== null ? "latest two periods" : "not available — see note below"}
        />
      </div>

      <AssumptionNote>{data.mom_note}</AssumptionNote>
      <div style={{ height: 12 }} />
      <AssumptionNote>{data.bookings_note}</AssumptionNote>

      <div style={{ height: 20 }} />

      <div className="chart-grid">
        <ChartCard title="Revenue by year" sub="Turnover, FY2024 vs FY2025 (€)">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={revenueByYear}>
              <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={{ stroke: "#d8ceb4" }} tickLine={false} />
              <YAxis tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => fmtEUR(v)} />
              <Bar dataKey="revenue" fill="#c99a3e" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Revenue mix by channel" sub={`FY2025 — Enterprise / Independent / R&D`}>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={channelData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={(d) => `${d.name} ${d.value}%`}>
                {channelData.map((_, i) => (
                  <Cell key={i} fill={CHANNEL_COLORS[i % CHANNEL_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => `${v}%`} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <ChartCard title="Geographic mix" sub="Ireland vs. outside Ireland, % of revenue (FY2024 figure is a derived approximation — see note below)">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={geoData} layout="vertical">
            <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="period" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} width={60} />
            <Tooltip formatter={(v) => `${v}%`} />
            <Legend />
            <Bar dataKey="Ireland" stackId="a" fill="#c99a3e" />
            <Bar dataKey="Outside Ireland" stackId="a" fill="#3e8e82" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Average Annual Contract Value by product (Enterprise, FY2025)" sub="Target: average ACV > €50,000 by FY2030">
        <table className="table">
          <thead>
            <tr><th>Product</th><th className="num">Avg. Enterprise ACV</th><th className="num">Subscription range</th></tr>
          </thead>
          <tbody>
            {data.product_acv.map((p) => (
              <tr key={p.product}>
                <td>{p.product}</td>
                <td className="num">{fmtEUR(p.avg_acv_enterprise)}</td>
                <td className="num">{fmtEUR(p.subscription_range_low)} – {fmtEUR(p.subscription_range_high)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ChartCard>
    </div>
  );
}