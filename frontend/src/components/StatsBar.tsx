"use client";

import { DailySummary } from "@/lib/api";

export default function StatsBar({ summary }: { summary: DailySummary }) {
  const stats = [
    { label: "涨停", value: summary.zt_count, unit: "只" },
    { label: "炸板", value: summary.zb_count, unit: "只" },
    { label: "最高连板", value: summary.max_lbc, unit: "板" },
    { label: "覆盖行业", value: summary.sector_count, unit: "个" },
    { label: "均涨幅", value: summary.avg_pct, unit: "%" },
  ];

  return (
    <div className="flex flex-wrap gap-3 w-full">
      {stats.map((s) => (
        <div
          key={s.label}
          className="flex items-baseline gap-1.5 glass rounded-xl px-4 py-3 min-w-0"
        >
          <span className="text-muted text-sm shrink-0">{s.label}</span>
          <span className="text-ink font-semibold text-2xl tabular-nums leading-none">
            {s.value}
          </span>
          <span className="text-muted text-sm">{s.unit}</span>
        </div>
      ))}
    </div>
  );
}
