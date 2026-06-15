"use client";

interface Props {
  data: { label: string; value: number }[];
  height?: number;
  width?: number;
  color?: string;
  pad?: number;
}

export default function BarChart({ data, height = 200, width = 600, color = "var(--primary)", pad = 30 }: Props) {
  if (!data.length) return null;

  const max = Math.max(...data.map((d) => d.value));
  const w = width - pad * 2;
  const h = height - pad * 2;
  const barW = Math.max(4, (w / data.length) * 0.7);
  const gap = w / data.length;

  const toX = (i: number) => pad + i * gap + (gap - barW) / 2;
  const toH = (v: number) => (v / (max || 1)) * h;
  const toY = (v: number) => h + pad - toH(v);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" preserveAspectRatio="xMidYMid meet">
      {/* Y axis */}
      {[0, 0.5, 1].map((pct) => {
        const val = max * pct;
        const y = toY(val);
        return (
          <g key={pct}>
            <line x1={pad} y1={y} x2={width - pad} y2={y} stroke="var(--border)" strokeWidth="0.5" />
            <text x={pad - 4} y={y + 4} textAnchor="end" fontSize="10" fill="var(--muted)">
              {val % 1 === 0 ? val : val.toFixed(0)}
            </text>
          </g>
        );
      })}

      {/* Bars */}
      {data.map((d, i) => (
        <g key={i}>
          <rect
            x={toX(i)}
            y={toY(d.value)}
            width={barW}
            height={toH(d.value)}
            fill={color}
            rx="2"
            ry="2"
          />
          {/* X label every Nth */}
          {(data.length <= 10 || i % Math.ceil(data.length / 7) === 0) && (
            <text x={toX(i) + barW / 2} y={height - 4} textAnchor="middle" fontSize="9" fill="var(--muted)">
              {d.label.length > 5 ? d.label.slice(5) : d.label}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
