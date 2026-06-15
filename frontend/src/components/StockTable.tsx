"use client";

import { useState, useMemo } from "react";
import { LimitUpStock } from "@/lib/api";

function formatAmount(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1e8) return `${(n / 1e8).toFixed(1)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(0)}万`;
  return String(n);
}

function formatTime(t: string | null | undefined): string {
  if (!t || t.length < 4) return "—";
  return `${t.slice(0, 2)}:${t.slice(2, 4)}`;
}

export default function StockTable({ stocks }: { stocks: LimitUpStock[] }) {
  const [industry, setIndustry] = useState<string>("全部");
  const [sortByLbc, setSortByLbc] = useState<boolean>(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");

  const industries = useMemo(() => {
    const set = new Set(stocks.map((s) => s.hybk));
    return ["全部", ...Array.from(set).sort()];
  }, [stocks]);

  const filtered = useMemo(() => {
    let list =
      industry === "全部"
        ? stocks
        : stocks.filter((s) => s.hybk === industry);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.code.includes(q) ||
          (s.reasons && s.reasons.toLowerCase().includes(q))
      );
    }
    list = [...list].sort((a, b) => {
      if (sortByLbc && (b.lbc || 0) !== (a.lbc || 0))
        return (b.lbc || 0) - (a.lbc || 0);
      return (b.pct || 0) - (a.pct || 0);
    });
    return list;
  }, [stocks, industry, sortByLbc, search]);

  const toggle = (code: string) => {
    const next = new Set(expanded);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    setExpanded(next);
  };

  return (
    <section className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
          涨停股{" "}
          <span className="text-ink font-semibold">{filtered.length}</span>
        </h2>
        <button
          onClick={() => setSortByLbc(!sortByLbc)}
          className={`text-sm px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer ${
            sortByLbc
              ? "bg-primary-a15 text-primary font-medium"
              : "glass text-muted hover:brightness-105"
          }`}
        >
          {sortByLbc ? "连板↓" : "涨幅↓"}
        </button>
      </div>

      {/* Search */}
      <div className="mb-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索股票代码、名称或原因..."
          className="w-full glass text-sm rounded-xl px-4 py-2.5 text-ink placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {/* Industry pills */}
      <div className="flex gap-1.5 overflow-x-auto pb-2 mb-2 -mx-1 px-1 scroll-smooth">
        {industries.map((ind) => (
          <button
            key={ind}
            onClick={() => setIndustry(ind)}
            className={`shrink-0 text-sm px-3 py-1.5 rounded-xl transition-colors cursor-pointer ${
              ind === industry
                ? "bg-primary text-white font-medium"
                : "glass text-muted hover:brightness-105"
            }`}
          >
            {ind}
          </button>
        ))}
      </div>

      {/* Stock cards */}
      <div className="flex flex-col gap-0.5">
        {filtered.map((s) => {
          const isExpanded = expanded.has(s.code);
          return (
            <div key={s.code}>
              <div
                className="px-4 py-3 rounded-xl glass hover:brightness-105 cursor-pointer transition-all md:cursor-default md:hover:brightness-100"
                onClick={() => toggle(s.code)}
              >
                <div className="flex items-center gap-3 md:gap-2">
                  {/* Left: name + code + lbc */}
                  <div className="flex-1 min-w-0 md:flex-none md:w-auto">
                    <div className="flex items-baseline gap-2 md:gap-1.5">
                      <span className="font-semibold text-base text-ink truncate">
                        {s.name}
                      </span>
                      <span className="text-xs text-muted tabular-nums tracking-wide shrink-0">
                        {s.code}
                      </span>
                      {s.lbc > 1 && (
                        <span className="shrink-0 inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-md text-xs font-bold bg-primary-a15 text-primary px-1">
                          {s.lbc}板
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-xs text-muted truncate">{s.hybk}</span>
                      {s.reasons && (
                        <span className="text-xs text-muted truncate hidden sm:inline">
                          {s.reasons.split("+").slice(0, 3).join(" · ")}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Middle: detail metrics — visible on md+ */}
                  <div className="hidden md:flex flex-1 items-center justify-end gap-x-3 text-xs text-muted mr-2">
                    <span>成交额 <span className="text-ink tabular-nums">{formatAmount(s.amount)}</span></span>
                    <span>换手率 <span className="text-ink tabular-nums">{s.hs?.toFixed(1)}%</span></span>
                    <span>封单 <span className="text-ink tabular-nums">{formatAmount(s.fund)}</span></span>
                    <span>炸板 <span className="text-ink tabular-nums">{s.zbc || 0}次</span></span>
                    <span>涨停统计 <span className="text-ink">{s.zttj || "—"}</span></span>
                  </div>

                  {/* Right: pct + time */}
                  <div className="text-right shrink-0">
                    <div className="text-lg font-bold tabular-nums text-up">
                      +{s.pct?.toFixed(1)}%
                    </div>
                    <div className="text-xs text-muted tabular-nums">
                      {formatTime(s.fbt)}
                    </div>
                  </div>
                </div>

                {/* Detail row: mobile only, shown when expanded */}
                <div className={`mt-2 pt-2 border-t border-border flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted md:hidden ${isExpanded ? '' : 'hidden'}`}>
                  <span>成交额 <span className="text-ink">{formatAmount(s.amount)}</span></span>
                  <span>换手率 <span className="text-ink">{s.hs?.toFixed(1)}%</span></span>
                  <span>封单 <span className="text-ink">{formatAmount(s.fund)}</span></span>
                  <span>炸板 <span className="text-ink">{s.zbc || 0}次</span></span>
                  <span>涨停统计 <span className="text-ink">{s.zttj || "—"}</span></span>
                  <span className="w-full text-xs text-muted">{s.reasons}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
