"use client";

import { useRouter } from "next/navigation";
import { TrendPoint } from "@/lib/api";
import LineChart from "@/components/charts/LineChart";
import BarChart from "@/components/charts/BarChart";

const PRESETS = [
  { days: 7, label: "7天" },
  { days: 14, label: "14天" },
  { days: 30, label: "30天" },
];

interface Props {
  trend: TrendPoint[];
  start: string;
  end: string;
}

export default function BacktestCharts({ trend, start, end }: Props) {
  const router = useRouter();

  function applyPreset(days: number) {
    const e = new Date();
    const s = new Date();
    s.setDate(s.getDate() - days);
    router.push(`/backtest?start=${s.toISOString().slice(0, 10)}&end=${e.toISOString().slice(0, 10)}`);
  }

  if (!trend.length) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <p className="text-muted text-sm">{start} ~ {end} 暂无数据</p>
        <p className="text-muted text-xs">该日期范围没有涨停记录</p>
      </div>
    );
  }

  const days = trend.map((t) => t.date);

  return (
    <>
      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted mr-1">周期：</span>
        {PRESETS.map((p) => {
          const daysDiff = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 86400000);
          const active = Math.abs(daysDiff - p.days) <= 1;
          return (
            <button
              key={p.days}
              onClick={() => applyPreset(p.days)}
              className={`text-sm px-3 py-1.5 rounded-xl transition-colors cursor-pointer ${
                active ? "bg-primary text-white font-medium" : "glass text-muted hover:brightness-105"
              }`}
            >
              {p.label}
            </button>
          );
        })}
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ZT Count Line */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">每日涨停数量</h3>
          <LineChart
            series={[
              {
                key: "zt_count",
                label: "涨停数",
                data: trend.map((t) => ({ label: t.date, value: t.zt_count })),
                color: "var(--up)",
                areaFill: true,
              },
            ]}
            height={200}
          />
        </div>

        {/* Max LBC Bar */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">最高连板数</h3>
          <BarChart
            data={trend.map((t) => ({ label: t.date, value: t.max_lbc }))}
            height={200}
            color="var(--primary)"
          />
        </div>

        {/* Avg Pct Line */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">平均涨幅趋势</h3>
          <LineChart
            series={[
              {
                key: "avg_pct",
                label: "平均涨幅%",
                data: trend.map((t) => ({ label: t.date, value: t.avg_pct })),
                color: "var(--up)",
              },
            ]}
            height={200}
          />
        </div>

        {/* Sector Count */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">覆盖行业数</h3>
          <LineChart
            series={[
              {
                key: "sectors",
                label: "行业数",
                data: trend.map((t) => ({ label: t.date, value: t.sector_count })),
                color: "var(--primary)",
                areaFill: true,
              },
            ]}
            height={200}
          />
        </div>
      </div>

      {/* Summary table */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-3 text-muted font-medium text-xs uppercase tracking-wider">日期</th>
                <th className="text-right px-4 py-3 text-muted font-medium text-xs uppercase tracking-wider">涨停数</th>
                <th className="text-right px-4 py-3 text-muted font-medium text-xs uppercase tracking-wider">平均涨幅</th>
                <th className="text-right px-4 py-3 text-muted font-medium text-xs uppercase tracking-wider">最高连板</th>
                <th className="text-right px-4 py-3 text-muted font-medium text-xs uppercase tracking-wider">覆盖行业</th>
              </tr>
            </thead>
            <tbody>
              {trend.map((t) => (
                <tr key={t.date} className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors">
                  <td className="px-4 py-2.5 text-ink tabular-nums">{t.date}</td>
                  <td className="px-4 py-2.5 text-right text-up font-semibold tabular-nums">{t.zt_count}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{t.avg_pct.toFixed(1)}%</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{t.max_lbc}板</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{t.sector_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
