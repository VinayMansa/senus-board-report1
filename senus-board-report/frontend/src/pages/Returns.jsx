import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Cell } from "recharts";
import api from "../api";
import { useSection } from "../hooks/useSection";
import { KpiCard, ChartCard, AssumptionNote, AiCommentary, Loading, ErrorBox, fmtEUR } from "../components/Widgets";

export default function Returns() {
  const { data, insight, loading, insightLoading, error, regenerate } = useSection(api.returns, "returns");

  if (error) return <ErrorBox message={error} />;
  if (loading || !data) return <Loading />;

  const acvEntries = Object.entries(data.avg_acv_enterprise_trend);
  const acvData = acvEntries.map(([name, value]) => ({ name, value }));
  const target = 50000;

  return (
    <div>
      <div className="page-header">
        <div className="page-eyebrow">Board Report</div>
        <h1 className="page-title">Returns</h1>
      </div>

      <AiCommentary insight={insight} onRegenerate={regenerate} loading={insightLoading} />

      <div className="kpi-row">
        <KpiCard label="ROCE" value={data.roce_status} tone="negative" />
        <KpiCard
          label="Average Enterprise ACV, FY2025"
          value={fmtEUR(acvEntries.reduce((s, [, v]) => s + v, 0) / acvEntries.length)}
          sub="target: >€50,000 by FY2030"
        />
      </div>

      <AssumptionNote>{data.roce_note}</AssumptionNote>

      <div style={{ height: 20 }} />

      <ChartCard title="Average Annual Contract Value by product (Enterprise, FY2025)" sub="Dashed line marks the FY2030 target of €50,000 average ACV">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={acvData}>
            <CartesianGrid stroke="#d8ceb4" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={{ stroke: "#d8ceb4" }} tickLine={false} />
            <YAxis tick={{ fill: "#5c6553", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`} />
            <Tooltip formatter={(v) => fmtEUR(v)} />
            <ReferenceLine y={target} stroke="#ab4a35" strokeDasharray="4 4" label={{ value: "FY2030 target", fill: "#ab4a35", fontSize: 12, position: "right" }} />
            <Bar dataKey="value" radius={[2, 2, 0, 0]}>
              {acvData.map((entry, i) => (
                <Cell key={i} fill={entry.value >= target ? "#6f8c4d" : "#c99a3e"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
