"use client";

interface Series {
  label: string;
  data: { label: string; value: number }[];
  color: string;
}

interface Props {
  leftSeries: Series;
  rightSeries: Series;
  height?: number;
  width?: number;
  pad?: number;
}

export default function DualAxisChart({
  leftSeries,
  rightSeries,
  height = 240,
  width = 600,
  pad = 40,
}: Props) {
  if (!leftSeries.data.length || !rightSeries.data.length) return null;

  // Left axis
  const leftValues = leftSeries.data.map((d) => d.value);
  const leftMin = Math.min(...leftValues, 0);
  const leftMax = Math.max(...leftValues);
  const leftRange = leftMax - leftMin || 1;

  // Right axis
  const rightValues = rightSeries.data.map((d) => d.value);
  const rightMin = Math.min(...rightValues);
  const rightMax = Math.max(...rightValues);
  const rightRange = rightMax - rightMin || 1;

  const labels = leftSeries.data.map((d) => d.label);
  const w = width - pad * 2;
  const h = height - pad * 2;

  const toX = (i: number) => pad + (labels.length > 1 ? (i / (labels.length - 1)) * w : w / 2);
  const toYLeft = (v: number) => h + pad - ((v - leftMin) / leftRange) * h;
  const toYRight = (v: number) => h + pad - ((v - rightMin) / rightRange) * h;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" preserveAspectRatio="xMidYMid meet">
      {/* Left Y axis */}
      {[0, 0.5, 1].map((pct) => {
        const y = toYLeft(leftMin + leftRange * pct);
        const val = leftMin + leftRange * pct;
        return (
          <text key={`l${pct}`} x={pad - 4} y={y + 4} textAnchor="end" fontSize="10" fill={leftSeries.color}>
            {val % 1 === 0 ? val : val.toFixed(0)}
          </text>
        );
      })}

      {/* Right Y axis */}
      {[0, 0.5, 1].map((pct) => {
        const y = toYRight(rightMin + rightRange * pct);
        const val = rightMin + rightRange * pct;
        return (
          <text key={`r${pct}`} x={width - pad + 4} y={y + 4} textAnchor="start" fontSize="10" fill={rightSeries.color}>
            {val % 1 === 0 ? val : val.toFixed(1)}
          </text>
        );
      })}

      {/* Grid lines */}
      {[0, 0.5, 1].map((pct) => (
        <line key={pct} x1={pad} y1={toYLeft(leftMin + leftRange * pct)} x2={width - pad} y2={toYLeft(leftMin + leftRange * pct)}
          stroke="var(--border)" strokeWidth="0.5" />
      ))}

      {/* Left series line */}
      <polyline
        points={leftSeries.data.map((d, i) => `${toX(i).toFixed(1)},${toYLeft(d.value).toFixed(1)}`).join(" ")}
        fill="none" stroke={leftSeries.color} strokeWidth="2" strokeLinecap="round"
      />

      {/* Right series line */}
      <polyline
        points={rightSeries.data.map((d, i) => `${toX(i).toFixed(1)},${toYRight(d.value).toFixed(1)}`).join(" ")}
        fill="none" stroke={rightSeries.color} strokeWidth="2" strokeLinecap="round" strokeDasharray="6 3"
      />

      {/* X labels */}
      {labels.map((l, i) => {
        const step = Math.max(1, Math.floor(labels.length / 7));
        if (i % step !== 0 && i !== labels.length - 1) return null;
        return (
          <text key={i} x={toX(i)} y={height - 4} textAnchor="middle" fontSize="10" fill="var(--muted)">
            {l.length > 5 ? l.slice(5) : l}
          </text>
        );
      })}

      {/* Threshold line annotation support — drawn as children by parent */}
    </svg>
  );
}
