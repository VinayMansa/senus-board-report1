import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import api from "../api";
import { KpiCard, fmtEUR, fmtPct, Loading, ErrorBox } from "../components/Widgets";

export default function Overview() {
  const [growth, setGrowth] = useState(null);
  const [profitability, setProfitability] = useState(null);
  const [cash, setCash] = useState(null);
  const [solvency, setSolvency] = useState(null);
  const [facts, setFacts] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.growth(), api.profitability(), api.cashLiquidity(), api.solvency(), api.corporateFacts()])
      .then(([g, p, c, s, f]) => {
        setGrowth(g); setProfitability(p); setCash(c); setSolvency(s); setFacts(f);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorBox message={error} />;
  if (!growth || !profitability || !cash || !solvency) return <Loading />;

  const chartData = growth.periods.map((label, i) => ({
    period: label,
    revenue: growth.revenue[i],
  }));

  return (
    <div>
      <div className="page-header">
        <div className="page-eyebrow">Senus PLC · {facts?.ticker} · {facts?.market}</div>
        <h1 className="page-title">Board Report</h1>
      </div>

      <div className="hero-metric">
        <div>
          <div className="hero-metric-label">FY2025 Revenue</div>
          <div className="hero-metric-value">
            {fmtEUR(growth.revenue[growth.revenue.length - 1])}
          </div>
          <div className={"hero-metric-delta " + (growth.revenue_yoy_growth_pct >= 0 ? "positive" : "negative")}>
            {fmtPct(growth.revenue_yoy_growth_pct, { showSign: true })} year-on-year
          </div>
        </div>
        <div className="hero-target">
          Senus 2030 target
          <strong>{growth.cagr_target_pct}% CAGR</strong>
          through FY2030, vs. €836,991 FY2025 base
        </div>
      </div>

      <div className="kpi-row">
        <KpiCard
          label="Gross margin"
          value={fmtPct(profitability.gross_margin_pct[profitability.gross_margin_pct.length - 1])}
          sub={`vs. ${fmtPct(profitability.gross_margin_pct[0])} FY2024`}
          tone="positive"
        />
        <KpiCard
          label="Operating margin"
          value={fmtPct(profitability.operating_margin_pct[profitability.operating_margin_pct.length - 1])}
          sub="loss-making, narrowing"
          tone="negative"
        />
        <KpiCard
          label="Closing cash (30 Jun 2025)"
          value={fmtEUR(cash.cash_end[cash.cash_end.length - 1])}
          sub={`≈ ${cash.cash_runway_months} months modelled runway`}
        />
        <KpiCard
          label="Net assets / (liabilities)"
          value={fmtEUR(solvency.net_assets_liabilities[solvency.net_assets_liabilities.length - 1])}
          sub="negative equity at FY2025 year-end"
          tone="negative"
        />
      </div>

      <div className="chart-card">
        <div className="chart-card-title">Revenue, FY2024–FY2025</div>
        <div className="chart-card-sub">Two years of disclosed historical revenue from the Information Document.</div>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData}>
            <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" />
            <XAxis dataKey="period" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={{ stroke: "#d8ceb4" }} tickLine={false} />
            <YAxis
              tick={{ fill: "#5c6553", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip formatter={(v) => fmtEUR(v)} contentStyle={{ fontFamily: "IBM Plex Sans", fontSize: 13, borderRadius: 3 }} />
            <Line type="monotone" dataKey="revenue" stroke="#c99a3e" strokeWidth={2.5} dot={{ r: 4, fill: "#c99a3e" }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-card">
        <div className="chart-card-title">Company snapshot</div>
        <table className="table">
          <tbody>
            <tr><td>Listing</td><td>{facts?.market} — {facts?.listing_date}</td></tr>
            <tr><td>Ticker / ISIN</td><td>{facts?.ticker} / {facts?.isin}</td></tr>
            <tr><td>Market cap at listing</td><td>{facts?.market_cap_at_listing}</td></tr>
            <tr><td>Employees</td><td>{facts?.employees}</td></tr>
            <tr><td>2025 Private Placement</td><td>{facts?.private_placement_proceeds} raised, post-money valuation {facts?.post_money_valuation}</td></tr>
            <tr><td>Strategy</td><td>{facts?.strategy_name} — CAGR ≥50% revenue growth, FY2026–FY2030</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
