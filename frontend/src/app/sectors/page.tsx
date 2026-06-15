import { fetchSectorRotation, fetchNarrativesRange, fetchAvailableDates } from "@/lib/api";
import DateNav from "@/components/DateNav";
import ThemeToggle from "@/components/ThemeToggle";
import NavBar from "@/components/NavBar";
import SectorCharts from "./SectorCharts";

function getDefaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 14);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

export default async function SectorsPage({
  searchParams,
}: {
  searchParams: Promise<{ start?: string; end?: string }>;
}) {
  const params = await searchParams;
  const defaults = getDefaultRange();
  const start = params.start || defaults.start;
  const end = params.end || defaults.end;

  const [rotation, narratives, dates] = await Promise.all([
    fetchSectorRotation(start, end),
    fetchNarrativesRange(start, end),
    fetchAvailableDates(),
  ]);

  return (
    <div className="flex flex-col flex-1 max-w-5xl mx-auto w-full px-4 py-6 sm:px-6 sm:py-8 gap-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <DateNav date={end} availableDates={dates} />
        <div className="flex items-center gap-3">
          <div className="text-xs text-muted">数据来源 AKShare · LLM 分析</div>
          <ThemeToggle />
        </div>
      </header>
      <NavBar />
      <SectorCharts rotation={rotation} narratives={narratives} start={start} end={end} />
      <footer className="text-center text-xs text-muted py-4 border-t border-border space-y-1">
        <p>涨停复盘 · 题材轮动追踪 · 数据仅供参考，不构成投资建议</p>
        <p>个人学习与 Vibe Coding 练习项目，仅供研究用途，非商业用途。</p>
      </footer>
    </div>
  );
}
