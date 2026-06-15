"use client";

interface Series {
  key: string;
  label: string;
  data: { label: string; value: number }[];
  color?: string;
  dashed?: boolean;
  areaFill?: boolean;
}

interface Props {
  series: Series[];
  height?: number;
  width?: number;
  pad?: number;
}

export default function LineChart({ series, height = 200, width = 600, pad = 30 }: Props) {
  if (!series.length || !series[0].data.length) return null;

  const allValues = series.flatMap((s) => s.data.map((d) => d.value));
  const min = Math.min(...allValues, 0);
  const max = Math.max(...allValues);
  const range = max - min || 1;
  const labels = series[0].data.map((d) => d.label);
  const w = width - pad * 2;
  const h = height - pad * 2;

  const toX = (i: number) => pad + (labels.length > 1 ? (i / (labels.length - 1)) * w : w / 2);
  const toY = (v: number) => h + pad - ((v - min) / range) * h;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" preserveAspectRatio="xMidYMid meet">
      {/* Y axis grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
        const y = toY(min + range * pct);
        const val = min + range * pct;
        return (
          <g key={pct}>
            <line x1={pad} y1={y} x2={width - pad} y2={y} stroke="var(--border)" strokeWidth="0.5" />
            <text x={pad - 4} y={y + 4} textAnchor="end" fontSize="10" fill="var(--muted)">
              {val % 1 === 0 ? val : val.toFixed(1)}
            </text>
          </g>
        );
      })}

      {/* X axis labels — every Nth */}
      {labels.map((l, i) => {
        const step = Math.max(1, Math.floor(labels.length / 7));
        if (i % step !== 0 && i !== labels.length - 1) return null;
        return (
          <text key={i} x={toX(i)} y={height - 4} textAnchor="middle" fontSize="10" fill="var(--muted)">
            {l.length > 5 ? l.slice(5) : l}
          </text>
        );
      })}

      {/* Series lines */}
      {series.map((s) => {
        const points = s.data.map((d, i) => `${toX(i).toFixed(1)},${toY(d.value).toFixed(1)}`).join(" ");
        const color = s.color || "var(--primary)";

        return (
          <g key={s.key}>
            {/* Area fill */}
            {s.areaFill && (
              <polygon
                points={`${toX(0)},${toY(min)} ${points} ${toX(s.data.length - 1)},${toY(min)}`}
                fill={color}
                opacity="0.1"
              />
            )}
            {/* Line */}
            <polyline
              points={points}
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray={s.dashed ? "4 4" : undefined}
            />
            {/* Legend dot + label */}
            <circle cx={width - pad - 120} cy={pad + series.indexOf(s) * 16} r="4" fill={color} />
            <text x={width - pad - 110} y={pad + series.indexOf(s) * 16 + 4} fontSize="11" fill="var(--muted)">
              {s.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
