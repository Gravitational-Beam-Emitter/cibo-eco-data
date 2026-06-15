"use client";

interface Props {
  rows: string[];
  cols: string[];
  data: number[][];
  cellSize?: number;
  colorMin?: string;
  colorMax?: string;
}

export default function Heatmap({
  rows,
  cols,
  data,
  cellSize = 24,
  colorMin = "var(--surface)",
  colorMax = "var(--primary)",
}: Props) {
  if (!rows.length || !cols.length) return null;

  const maxVal = Math.max(...data.flat(), 1);
  const labelW = Math.max(...rows.map((r) => r.length)) * 8 + 16;
  const w = labelW + cols.length * cellSize + 40;
  const h = 24 + rows.length * cellSize + 40;

  // color-mix simulation via opacity
  function cellColor(v: number): string {
    if (v === 0) return colorMin;
    return `color-mix(in oklch, ${colorMax} ${Math.round((v / maxVal) * 100)}%, ${colorMin})`;
  }

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} className="shrink-0">
        {/* Column labels (dates) */}
        {cols.map((c, ci) => (
          <text
            key={ci}
            x={labelW + ci * cellSize + cellSize / 2}
            y={20}
            textAnchor="start"
            fontSize="9"
            fill="var(--muted)"
            transform={`rotate(-45, ${labelW + ci * cellSize + cellSize / 2}, 20)`}
          >
            {c.length > 5 ? c.slice(5) : c}
          </text>
        ))}

        {/* Row labels + cells */}
        {rows.map((r, ri) => (
          <g key={ri}>
            <text
              x={labelW - 4}
              y={32 + ri * cellSize + cellSize / 2 + 4}
              textAnchor="end"
              fontSize="10"
              fill="var(--muted)"
            >
              {r}
            </text>
            {cols.map((_c, ci) => {
              const v = data[ri]?.[ci] || 0;
              return (
                <g key={ci}>
                  <rect
                    x={labelW + ci * cellSize}
                    y={24 + ri * cellSize}
                    width={cellSize - 1}
                    height={cellSize - 1}
                    fill={cellColor(v)}
                    rx="3"
                    ry="3"
                  />
                  {v > 0 && (
                    <text
                      x={labelW + ci * cellSize + cellSize / 2}
                      y={24 + ri * cellSize + cellSize / 2 + 4}
                      textAnchor="middle"
                      fontSize="9"
                      fill={v / maxVal > 0.5 ? "var(--bg)" : "var(--ink)"}
                    >
                      {v}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        ))}
      </svg>
    </div>
  );
}
