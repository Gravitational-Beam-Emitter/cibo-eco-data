"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { SectorRotation, Narrative } from "@/lib/api";
import Heatmap from "@/components/charts/Heatmap";

const CARD_COLORS = [
  "var(--card-0)", "var(--card-1)", "var(--card-2)", "var(--card-3)", "var(--card-4)",
];

const PRESETS = [
  { days: 7, label: "7天" },
  { days: 14, label: "14天" },
  { days: 30, label: "30天" },
];

interface Props {
  rotation: SectorRotation;
  narratives: Narrative[];
  start: string;
  end: string;
}

export default function SectorCharts({ rotation, narratives, start, end }: Props) {
  const router = useRouter();

  function applyPreset(days: number) {
    const e = new Date();
    const s = new Date();
    s.setDate(s.getDate() - days);
    router.push(`/sectors?start=${s.toISOString().slice(0, 10)}&end=${e.toISOString().slice(0, 10)}`);
  }

  // Build per-day top-5 sectors
  const dailyTop = useMemo(() => {
    if (!rotation.days.length || !rotation.sectors.length) return [];
    return rotation.days.map((day, di) => {
      const ranked = rotation.sectors
        .map((sector, si) => ({ sector, count: rotation.matrix[si]?.[di] || 0 }))
        .filter((s) => s.count > 0)
        .sort((a, b) => b.count - a.count)
        .slice(0, 5);
      return { date: day, top: ranked };
    });
  }, [rotation]);

  // Emerging / fading sectors
  const momentum = useMemo(() => {
    if (rotation.days.length < 5 || !rotation.sectors.length) return { emerging: [], fading: [] };
    const days = rotation.days;
    const half = Math.floor(days.length / 2);
    const recentDays = days.slice(-3);
    const priorDays = days.slice(0, Math.max(0, days.length - 3));

    const scores: { sector: string; recent: number; total: number; delta: number }[] = [];
    rotation.sectors.forEach((sector, si) => {
      let total = 0;
      let recent = 0;
      let prior = 0;
      rotation.days.forEach((_d, di) => {
        const v = rotation.matrix[si]?.[di] || 0;
        total += v;
        if (rotation.days.indexOf(rotation.days[di]) >= days.length - 3) recent += v;
        else prior += v;
      });
      const priorLen = Math.max(1, priorDays.length || 1);
      const recentLen = recentDays.length;
      const recentAvg = recent / recentLen;
      const priorAvg = prior / priorLen;
      const delta = priorAvg > 0 ? recentAvg - priorAvg : recentAvg;
      scores.push({ sector, recent: recentAvg, total, delta });
    });

    const sorted = scores.filter((s) => s.total > 0).sort((a, b) => b.delta - a.delta);
    return {
      emerging: sorted.filter((s) => s.delta > 1).slice(0, 5),
      fading: sorted.filter((s) => s.delta < -1).reverse().slice(0, 5),
    };
  }, [rotation]);

  if (!rotation.days.length) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <p className="text-muted text-sm">{start} ~ {end} 暂无数据</p>
        <p className="text-muted text-xs">该日期范围没有涨停记录</p>
      </div>
    );
  }

  return (
    <>
      {/* Preset buttons */}
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

      {/* Heatmap */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">行业热度矩阵</h3>
        {rotation.matrix.length > 0 ? (
          <Heatmap
            rows={rotation.sectors}
            cols={rotation.days}
            data={rotation.matrix}
            cellSize={28}
          />
        ) : (
          <p className="text-xs text-muted">暂无行业数据</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top sectors by day */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">每日 Top 5 行业</h3>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {dailyTop.map((dt, i) => (
              <div
                key={dt.date}
                className="shrink-0 w-48 rounded-xl p-3"
                style={{ background: CARD_COLORS[i % CARD_COLORS.length] }}
              >
                <div className="text-xs font-semibold text-ink mb-2">{dt.date.slice(5)}</div>
                {dt.top.map((s, j) => (
                  <div key={j} className="flex justify-between text-xs mb-1">
                    <span className="text-ink truncate">{s.sector}</span>
                    <span className="text-up tabular-nums ml-2">{s.count}只</span>
                  </div>
                ))}
                {dt.top.length === 0 && <p className="text-xs text-muted">无数据</p>}
              </div>
            ))}
          </div>
        </div>

        {/* Emerging / fading */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">板块动量变化</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-medium text-up mb-2">上升趋势</div>
              {momentum.emerging.map((s, i) => (
                <div key={i} className="flex items-center justify-between text-xs mb-1">
                  <span className="text-ink truncate">{s.sector}</span>
                  <span className="text-up tabular-nums">+{s.delta.toFixed(1)}</span>
                </div>
              ))}
              {momentum.emerging.length === 0 && (
                <p className="text-xs text-muted">数据不足</p>
              )}
            </div>
            <div>
              <div className="text-xs font-medium text-down mb-2">降温趋势</div>
              {momentum.fading.map((s, i) => (
                <div key={i} className="flex items-center justify-between text-xs mb-1">
                  <span className="text-ink truncate">{s.sector}</span>
                  <span className="text-down tabular-nums">{s.delta.toFixed(1)}</span>
                </div>
              ))}
              {momentum.fading.length === 0 && (
                <p className="text-xs text-muted">数据不足</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Narrative evolution */}
      {narratives.length > 0 && (
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">主线叙事演变</h3>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {/* Group by date */}
            {(() => {
              const byDate = new Map<string, Narrative[]>();
              narratives.forEach((n) => {
                const d = n.date;
                if (!byDate.has(d)) byDate.set(d, []);
                byDate.get(d)!.push(n);
              });
              const allNames = new Set(narratives.map((n) => n.name));
              return Array.from(byDate.entries())
                .sort((a, b) => b[0].localeCompare(a[0]))
                .map(([date, items], i) => (
                  <div
                    key={date}
                    className="shrink-0 w-56 rounded-xl p-3"
                    style={{ background: CARD_COLORS[i % CARD_COLORS.length] }}
                  >
                    <div className="text-xs font-semibold text-ink mb-2">{date.slice(5)}</div>
                    {items.map((n, j) => (
                      <div key={j} className="mb-2 last:mb-0">
                        <div className="text-sm text-ink font-medium">
                          {n.name}
                        </div>
                        <div className="text-xs text-muted line-clamp-2 mt-0.5">{n.description}</div>
                      </div>
                    ))}
                  </div>
                ));
            })()}
          </div>
        </div>
      )}
    </>
  );
}
