"use client";

import { useState } from "react";
import { MacroIndicator } from "@/lib/api";

const LABELS: Record<number, string> = {
  5: "制造业PMI",
  7: "M2",
  8: "LPR",
  14: "70城房价",
  53: "WTI原油",
  32: "美联储利率",
};

function formatValue(value: number | null, id: number): string {
  if (value == null) return "—";
  switch (id) {
    case 5: return value.toFixed(1);
    case 7: return `${(value / 10000).toFixed(1)}万亿`;
    case 8: return `${value.toFixed(2)}%`;
    case 14: return value.toFixed(1);
    case 53: return `$${value.toFixed(0)}`;
    case 32: return `${value.toFixed(2)}%`;
    default: return String(value);
  }
}

function formatDate(date: string | null): string {
  if (!date) return "";
  const d = new Date(date);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function getAnomaly(id: number, value: number | null): "up" | "down" | null {
  if (value == null) return null;
  switch (id) {
    case 5: return value >= 50 ? "up" : "down";       // PMI
    case 14: return value >= 100 ? "up" : "down";      // House price index
    case 8: return value <= 3.5 ? "up" : "down";       // LPR (lower = looser)
    case 32: return value <= 4.0 ? "up" : "down";      // Fed funds (lower = looser)
    default: return null;
  }
}

function Sparkline({ data, id }: { data: { date: string; value: number }[]; id: number }) {
  if (!data.length) return null;
  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 200;
  const h = 32;
  const pad = 2;

  const points = values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (w - pad * 2);
      const y = h - pad - ((v - min) / range) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const stroke = id === 5 && values[values.length - 1] < 50 ? "var(--down)" : "var(--up)";

  return (
    <svg width={w} height={h} className="shrink-0">
      <polyline
        points={points}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function MacroBar({ indicators }: { indicators: MacroIndicator[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!indicators.length) return null;

  return (
    <section className="w-full">
      <h2 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">
        宏观背景
      </h2>
      <div className="flex flex-wrap gap-2">
        {indicators.map((ind) => {
          const isOpen = expanded === ind.id;
          const anomaly = getAnomaly(ind.id, ind.value);
          const valueColor = anomaly === "up" ? "text-up" : anomaly === "down" ? "text-down" : "text-ink";

          return (
            <div key={ind.id}>
              <div
                className={`flex items-center gap-2 glass rounded-xl px-4 py-2.5 cursor-pointer transition-all hover:brightness-105 ${
                  isOpen ? "rounded-b-none" : ""
                }`}
                onClick={() => setExpanded(isOpen ? null : ind.id)}
              >
                <span className="text-xs text-muted shrink-0">
                  {LABELS[ind.id] || ind.name}
                </span>
                <span className={`text-base font-semibold tabular-nums ${valueColor}`}>
                  {formatValue(ind.value, ind.id)}
                </span>
                <span className="text-xs text-muted shrink-0">
                  {formatDate(ind.date)}
                </span>
              </div>

              {isOpen && ind.history.length > 0 && (
                <div className="glass border-t border-border rounded-b-xl px-4 py-2 flex items-center gap-3">
                  <Sparkline data={ind.history} id={ind.id} />
                  <div className="flex gap-x-3 gap-y-0.5 flex-wrap text-xs text-muted">
                    <span>最新 <span className="text-ink tabular-nums">{formatValue(ind.value, ind.id)}</span></span>
                    <span>均值 <span className="text-ink tabular-nums">{formatValue(ind.history.reduce((s, d) => s + d.value, 0) / ind.history.length, ind.id)}</span></span>
                    <span>最高 <span className="text-ink tabular-nums">{formatValue(Math.max(...ind.history.map((d) => d.value)), ind.id)}</span></span>
                    <span>最低 <span className="text-ink tabular-nums">{formatValue(Math.min(...ind.history.map((d) => d.value)), ind.id)}</span></span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
