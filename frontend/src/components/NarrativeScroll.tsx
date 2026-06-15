"use client";

import { Narrative } from "@/lib/api";

const CARD_COLORS = [
  "var(--card-0)",
  "var(--card-1)",
  "var(--card-2)",
  "var(--card-3)",
  "var(--card-4)",
];

export default function NarrativeScroll({
  narratives,
}: {
  narratives: Narrative[];
}) {
  if (!narratives.length) return null;

  return (
    <section className="w-full">
      <h2 className="text-sm font-medium text-muted uppercase tracking-wider mb-3">
        市场主线
      </h2>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 snap-x scroll-smooth">
        {narratives.map((n, i) => (
          <div
            key={n.name}
            className="shrink-0 w-72 rounded-2xl p-4 snap-start hover:brightness-110 transition-all cursor-default shadow-lg"
            style={{ background: CARD_COLORS[i % CARD_COLORS.length] }}
          >
            <h3 className="font-semibold text-base text-ink mb-2">{n.name}</h3>
            <p className="text-muted text-sm leading-relaxed mb-3 line-clamp-3">
              {n.description}
            </p>
            <div className="flex flex-wrap gap-1">
              {n.stocks.slice(0, 6).map((s) => (
                <span
                  key={s.code}
                  className="text-xs px-1.5 py-0.5 rounded-lg bg-bg text-muted"
                >
                  {s.name}
                  {s.lbc > 1 ? ` ${s.lbc}板` : ""}
                </span>
              ))}
              {n.stocks.length > 6 && (
                <span className="text-xs text-muted">
                  +{n.stocks.length - 6}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
