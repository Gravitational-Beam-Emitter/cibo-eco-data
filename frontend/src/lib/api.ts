const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";
const ECO_API = process.env.NEXT_PUBLIC_ECO_API_URL || "http://127.0.0.1:8000";

export interface LimitUpStock {
  date: string;
  code: string;
  name: string;
  price: number;
  pct: number;
  amount: number;
  ltsz: number;
  zsz: number;
  hs: number;
  fund: number;
  fbt: string;
  lbt: string;
  zbc: number;
  zttj: string;
  lbc: number;
  hybk: string;
  reasons: string | null;
}

export interface DailySummary {
  date: string;
  zt_count: number;
  avg_pct: number;
  max_lbc: number;
  zb_count: number;
  sector_count: number;
}

export interface Narrative {
  date: string;
  tag: string;
  name: string;
  description: string;
  stocks: { code: string; name: string; lbc: number }[];
}

export interface IndustryStat {
  industry: string;
  count: number;
  avg_pct: number;
  max_lbc: number;
}

export interface DailyReview {
  date: string;
  summary: DailySummary;
  stocks: LimitUpStock[];
  narratives: Narrative[];
  industries: IndustryStat[];
}

export interface StockHistory {
  code: string;
  count: number;
  history: LimitUpStock[];
}

export async function fetchDailyReview(date: string): Promise<DailyReview> {
  const res = await fetch(`${API_BASE}/api/v1/daily/${date}`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`Failed to fetch daily review: ${res.status}`);
  return res.json();
}

export async function fetchStockHistory(code: string): Promise<StockHistory> {
  const res = await fetch(`${API_BASE}/api/v1/stock/${code}`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`Failed to fetch stock history: ${res.status}`);
  return res.json();
}

export async function fetchAvailableDates(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/v1/dates`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return data.dates || [];
}

export async function triggerFetch(date?: string): Promise<void> {
  const params = date ? `?date=${date}` : "";
  await fetch(`${API_BASE}/api/v1/fetch${params}`, { method: "POST" });
}

/* ── Macro indicators (eco data API :8000) ── */

export interface MacroIndicator {
  id: number;
  name: string;
  frequency: string;
  value: number | null;
  date: string | null;
  history: { date: string; value: number }[];
}

const MACRO_IDS = [5, 7, 8, 14, 53, 32]; // PMI, M2, LPR, HousePrice, WTI, FedFunds

export async function fetchMacroBackground(): Promise<MacroIndicator[]> {
  const results = await Promise.all(
    MACRO_IDS.map(async (id) => {
      try {
        const [latestRes, histRes] = await Promise.all([
          fetch(`${ECO_API}/api/v1/data/${id}/latest`, { next: { revalidate: 600 } }),
          fetch(`${ECO_API}/api/v1/data/${id}?limit=12`, { next: { revalidate: 600 } }),
        ]);
        if (!latestRes.ok) return { id, name: "", frequency: "", value: null, date: null, history: [] };
        const [latestData, histData] = await Promise.all([latestRes.json(), histRes.ok ? histRes.json() : null]);
        return {
          id,
          name: latestData.indicator?.name || "",
          frequency: latestData.indicator?.frequency || "",
          value: latestData.latest?.value ?? null,
          date: latestData.latest?.date ?? null,
          history: histData?.data?.reverse().map((o: { date: string; value: number }) => ({
            date: o.date.slice(0, 10), value: o.value,
          })) || [],
        };
      } catch {
        return { id, name: "", frequency: "", value: null, date: null, history: [] };
      }
    })
  );
  return results;
}
