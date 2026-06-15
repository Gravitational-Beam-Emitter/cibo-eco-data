"use client";

import { useState, useMemo } from "react";
import { TrendPoint, MacroSeries } from "@/lib/api";
import DualAxisChart from "@/components/charts/DualAxisChart";
import CorrelationScatter from "@/components/charts/CorrelationScatter";
import LineChart from "@/components/charts/LineChart";

interface Props {
  trend: TrendPoint[];
  macro: MacroSeries[];
  start: string;
  end: string;
}

function formatMacroValue(id: number, value: number): string {
  switch (id) {
    case 7: return `${(value / 10000).toFixed(1)}万亿`;
    case 8: return `${value.toFixed(2)}%`;
    case 5: return value.toFixed(1);
    case 14: return value.toFixed(1);
    case 53: return `$${value.toFixed(0)}`;
    case 32: return `${value.toFixed(2)}%`;
    default: return String(value);
  }
}

const THRESHOLDS: Record<number, { value: number; label: string }> = {
  5: { value: 50, label: "荣枯线 50" },
  8: { value: 3.5, label: "3.5%" },
  32: { value: 4.0, label: "4.0%" },
};

export default function CrossCharts({ trend, macro, start, end }: Props) {
  const [selectedMacro, setSelectedMacro] = useState<number>(5);
  const [selectedZT, setSelectedZT] = useState<"zt_count" | "avg_pct" | "max_lbc">("zt_count");

  const selectedMacroData = useMemo(
    () => macro.find((m) => m.id === selectedMacro) || { id: selectedMacro, name: "", data: [] },
    [macro, selectedMacro]
  );

  // Align dates for dual-axis chart
  const alignedData = useMemo(() => {
    if (!trend.length || !selectedMacroData.data.length) return { left: [], right: [] };
    // Forward-fill macro values to match trading days
    const macroByDate = new Map<string, number>();
    selectedMacroData.data.forEach((d) => macroByDate.set(d.date, d.value));

    let lastMacroVal = 0;
    const left: { label: string; value: number }[] = [];
    const right: { label: string; value: number }[] = [];

    trend.forEach((t) => {
      const macroVal = macroByDate.get(t.date);
      if (macroVal !== undefined) lastMacroVal = macroVal;
      const ztVal = t[selectedZT];
      if (lastMacroVal > 0 && ztVal > 0) {
        left.push({ label: t.date, value: ztVal });
        right.push({ label: t.date, value: lastMacroVal });
      }
    });

    return { left, right };
  }, [trend, selectedMacroData.data, selectedZT]);

  // Correlation data
  const scatterPoints = useMemo(() => {
    if (!trend.length || !selectedMacroData.data.length) return [];
    const macroByDate = new Map<string, number>();
    selectedMacroData.data.forEach((d) => macroByDate.set(d.date, d.value));

    let lastVal = 0;
    return trend
      .filter((t) => {
        const mv = macroByDate.get(t.date);
        if (mv !== undefined) lastVal = mv;
        return lastVal > 0 && t[selectedZT] > 0;
      })
      .map((t) => ({ x: lastVal, y: t[selectedZT], label: t.date.slice(5) }));
  }, [trend, selectedMacroData.data, selectedZT]);

  const ZT_LABELS: Record<string, string> = { zt_count: "涨停数", avg_pct: "平均涨幅%", max_lbc: "最高连板" };

  const threshold = THRESHOLDS[selectedMacro];

  if (!trend.length) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <p className="text-muted text-sm">暂无涨停数据</p>
      </div>
    );
  }

  return (
    <>
      {/* Selectors */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">宏观指标：</span>
          {macro.filter((m) => m.data.length > 0).map((m) => (
            <button
              key={m.id}
              onClick={() => setSelectedMacro(m.id)}
              className={`text-sm px-3 py-1.5 rounded-xl transition-colors cursor-pointer ${
                m.id === selectedMacro ? "bg-primary text-white font-medium" : "glass text-muted hover:brightness-105"
              }`}
            >
              {m.name || `#${m.id}`}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">涨停指标：</span>
          {Object.entries(ZT_LABELS).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSelectedZT(key as typeof selectedZT)}
              className={`text-sm px-3 py-1.5 rounded-xl transition-colors cursor-pointer ${
                key === selectedZT ? "bg-primary-a15 text-primary font-medium" : "glass text-muted hover:brightness-105"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Dual axis chart */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">
          {selectedMacroData.name || `指标 #${selectedMacro}`} vs {ZT_LABELS[selectedZT]}
        </h3>
        {alignedData.left.length > 0 ? (
          <DualAxisChart
            leftSeries={{ label: ZT_LABELS[selectedZT], data: alignedData.left, color: "var(--up)" }}
            rightSeries={{ label: selectedMacroData.name, data: alignedData.right, color: "var(--primary)" }}
            height={260}
          />
        ) : (
          <p className="text-xs text-muted py-8 text-center">日期对齐数据不足</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Correlation scatter */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">
            {selectedMacroData.name} vs {ZT_LABELS[selectedZT]} 相关性
          </h3>
          <CorrelationScatter
            points={scatterPoints}
            xLabel={selectedMacroData.name}
            yLabel={ZT_LABELS[selectedZT]}
            height={280}
          />
        </div>

        {/* Macro trend alone */}
        <div className="glass rounded-xl p-4">
          <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">
            {selectedMacroData.name} 走势
          </h3>
          {selectedMacroData.data.length > 0 ? (
            <LineChart
              series={[
                {
                  key: "macro",
                  label: selectedMacroData.name,
                  data: selectedMacroData.data.map((d) => ({ label: d.date, value: d.value })),
                  color: "var(--primary)",
                  areaFill: true,
                },
              ]}
              height={280}
            />
          ) : (
            <p className="text-xs text-muted py-8 text-center">无宏观数据</p>
          )}
          {threshold && (
            <p className="text-xs text-muted mt-2">
              * {threshold.label} 参考线（{selectedMacroData.name}）
            </p>
          )}
        </div>
      </div>

      {/* Multi-macro overlay — all macro indicators normalized */}
      <div className="glass rounded-xl p-4">
        <h3 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">多指标走势对比（标准化）</h3>
        {macro.filter((m) => m.data.length > 0).length > 0 ? (
          <LineChart
            series={macro
              .filter((m) => m.data.length > 0)
              .map((m, i) => {
                const values = m.data.map((d) => d.value);
                const avg = values.reduce((a, b) => a + b, 0) / values.length || 1;
                const colors = ["var(--up)", "var(--primary)", "var(--down)", "var(--muted)", "oklch(0.6 0.15 250)"];
                return {
                  key: String(m.id),
                  label: m.name || `#${m.id}`,
                  data: m.data.map((d) => ({ label: d.date, value: (d.value / avg) * 100 })),
                  color: colors[i % colors.length],
                };
              })}
            height={240}
          />
        ) : (
          <p className="text-xs text-muted py-8 text-center">无宏观数据</p>
        )}
      </div>
    </>
  );
}
