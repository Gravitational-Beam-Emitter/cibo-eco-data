"use client";

interface Props {
  points: { x: number; y: number; label?: string }[];
  xLabel?: string;
  yLabel?: string;
  height?: number;
  width?: number;
  pad?: number;
}

function pearsonR(xs: number[], ys: number[]): number {
  const n = xs.length;
  if (n < 3) return 0;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, dx2 = 0, dy2 = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx;
    const dy = ys[i] - my;
    num += dx * dy;
    dx2 += dx * dx;
    dy2 += dy * dy;
  }
  const den = Math.sqrt(dx2) * Math.sqrt(dy2);
  return den === 0 ? 0 : num / den;
}

function linearRegression(xs: number[], ys: number[]): { slope: number; intercept: number } | null {
  const n = xs.length;
  if (n < 2) return null;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) {
    num += (xs[i] - mx) * (ys[i] - my);
    den += (xs[i] - mx) ** 2;
  }
  if (den === 0) return null;
  const slope = num / den;
  return { slope, intercept: my - slope * mx };
}

export default function CorrelationScatter({
  points,
  xLabel = "宏观指标",
  yLabel = "涨停数",
  height = 280,
  width = 500,
  pad = 40,
}: Props) {
  if (points.length < 3) {
    return <p className="text-xs text-muted p-4">数据点不足，无法分析相关性</p>;
  }

  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const xRange = xMax - xMin || 1;
  const xPad = xRange * 0.1;
  const yMin = Math.min(...ys, 0);
  const yMax = Math.max(...ys);
  const yRange = yMax - yMin || 1;
  const yPad = yRange * 0.1;

  const r = pearsonR(xs, ys);
  const reg = linearRegression(xs, ys);

  const toX = (v: number) => pad + ((v - (xMin - xPad)) / (xRange + xPad * 2)) * (width - pad * 2);
  const toY = (v: number) => height - pad - ((v - (yMin - yPad)) / (yRange + yPad * 2)) * (height - pad * 2);

  const rLabel =
    Math.abs(r) >= 0.7 ? "强相关" : Math.abs(r) >= 0.4 ? "中等相关" : "弱相关";

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" preserveAspectRatio="xMidYMid meet">
      {/* Grid */}
      {[0, 0.5, 1].map((pct) => (
        <line key={pct} x1={pad} y1={toY(yMin + yRange * pct)} x2={width - pad} y2={toY(yMin + yRange * pct)}
          stroke="var(--border)" strokeWidth="0.5" />
      ))}

      {/* Regression line */}
      {reg && (
        <line
          x1={toX(xMin - xPad)} y1={toY(reg.intercept + reg.slope * (xMin - xPad))}
          x2={toX(xMax + xPad)} y2={toY(reg.intercept + reg.slope * (xMax + xPad))}
          stroke="var(--muted)" strokeWidth="1" strokeDasharray="4 3"
        />
      )}

      {/* Points */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={toX(p.x)} cy={toY(p.y)} r="4" fill="var(--primary)" opacity="0.7" />
          {p.label && (
            <text x={toX(p.x)} y={toY(p.y) - 8} textAnchor="middle" fontSize="9" fill="var(--muted)">
              {p.label}
            </text>
          )}
        </g>
      ))}

      {/* Correlation label */}
      <text x={width - pad} y={pad + 4} textAnchor="end" fontSize="13" fill="var(--ink)" fontWeight="600">
        r = {r.toFixed(3)}
      </text>
      <text x={width - pad} y={pad + 18} textAnchor="end" fontSize="11" fill={Math.abs(r) >= 0.5 ? "var(--up)" : "var(--muted)"}>
        {rLabel}{r > 0 ? " 正相关" : " 负相关"}
      </text>

      {/* Axis labels */}
      <text x={width / 2} y={height - 2} textAnchor="middle" fontSize="10" fill="var(--muted)">{xLabel}</text>
      <text x={6} y={height / 2} textAnchor="middle" fontSize="10" fill="var(--muted)"
        transform={`rotate(-90, 6, ${height / 2})`}>{yLabel}</text>
    </svg>
  );
}
