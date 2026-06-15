import { fetchDailyReview, fetchAvailableDates, fetchMacroBackground } from "@/lib/api";
import DateNav from "@/components/DateNav";
import ThemeToggle from "@/components/ThemeToggle";
import StatsBar from "@/components/StatsBar";
import MacroBar from "@/components/MacroBar";
import NarrativeScroll from "@/components/NarrativeScroll";
import StockTable from "@/components/StockTable";

// Safe wrapper — returns empty review on error
async function getReview(date: string) {
  try {
    return await fetchDailyReview(date);
  } catch {
    return null;
  }
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const { date } = await searchParams;
  const today = new Date().toISOString().slice(0, 10);
  const targetDate = date || today;

  const [review, dates, macro] = await Promise.all([
    getReview(targetDate),
    fetchAvailableDates(),
    fetchMacroBackground(),
  ]);

  return (
    <div className="flex flex-col flex-1 max-w-5xl mx-auto w-full px-4 py-6 sm:px-6 sm:py-8 gap-6">
      {/* Header */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <DateNav date={targetDate} availableDates={dates} />
        <div className="flex items-center gap-3">
          <div className="text-xs text-muted">
            数据来源 AKShare · LLM 分析
          </div>
          <ThemeToggle />
        </div>
      </header>

      {!review ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <p className="text-muted text-sm">
            {targetDate} 暂无数据
          </p>
          <p className="text-muted text-xs">
            可能是非交易日，或数据尚未拉取
          </p>
        </div>
      ) : (
        <>
          {/* Stats */}
          <StatsBar summary={review.summary} />

          {/* Macro background */}
          <MacroBar indicators={macro} />

          {/* Narratives */}
          <NarrativeScroll narratives={review.narratives} />

          {/* Stock table */}
          <StockTable stocks={review.stocks} />
        </>
      )}

      {/* Footer */}
      <footer className="text-center text-xs text-muted py-4 border-t border-border space-y-1">
        <p>涨停复盘 · 数据仅供参考，不构成投资建议</p>
        <p>个人学习与 Vibe Coding 练习项目，仅供研究用途，非商业用途。数据来源 AKShare，LLM 分析仅供参考。</p>
      </footer>
    </div>
  );
}
