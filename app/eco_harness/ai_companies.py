"""
AI Company Financials Harness — tracks key financial metrics for AI supply chain.

Data sources:
  - yfinance (Yahoo Finance) — quarterly revenue, net income, CapEx
  - Free, no API key required

Covers:
  - AI chip makers: NVIDIA, TSMC, Broadcom
  - Semiconductor equipment: ASML
  - Hyperscalers: Microsoft, Amazon, Google, Meta
  - Aggregate: total hyperscaler CapEx and revenue

All returns pd.DataFrame with date/value columns.
"""

from __future__ import annotations

import pandas as pd


class AICompaniesHarness:
    """AI supply chain company financials via yfinance."""

    _YF_CACHE: dict = {}  # simple module-level cache

    def _get_ticker(self, symbol: str):
        if symbol not in self._YF_CACHE:
            import yfinance as yf
            self._YF_CACHE[symbol] = yf.Ticker(symbol)
        return self._YF_CACHE[symbol]

    def _quarterly_revenue(self, symbol: str) -> pd.DataFrame:
        """Extract quarterly total revenue as pd.DataFrame."""
        tk = self._get_ticker(symbol)
        qf = tk.quarterly_financials
        if qf is None or qf.empty:
            return pd.DataFrame(columns=["date", "value"])
        for idx in qf.index:
            if "Total Revenue" in str(idx):
                s = qf.loc[idx]
                return self._series_to_df(s)
        return pd.DataFrame(columns=["date", "value"])

    def _quarterly_net_income(self, symbol: str) -> pd.DataFrame:
        """Extract quarterly net income."""
        tk = self._get_ticker(symbol)
        qf = tk.quarterly_financials
        if qf is None or qf.empty:
            return pd.DataFrame(columns=["date", "value"])
        for idx in qf.index:
            if str(idx).strip() == "Net Income":
                s = qf.loc[idx]
                return self._series_to_df(s)
        # Fallback: "Net Income Common Stockholders"
        for idx in qf.index:
            if "Net Income" in str(idx) and "Common" in str(idx):
                s = qf.loc[idx]
                return self._series_to_df(s)
        return pd.DataFrame(columns=["date", "value"])

    def _quarterly_capex(self, symbol: str) -> pd.DataFrame:
        """Extract quarterly capital expenditure (positive value = spending)."""
        tk = self._get_ticker(symbol)
        cf = tk.cashflow
        if cf is None or cf.empty:
            return pd.DataFrame(columns=["date", "value"])
        for idx in cf.index:
            if "Capital Expenditure" in str(idx) or "Capital Expenditures" in str(idx):
                s = cf.loc[idx]
                df = self._series_to_df(s)
                # CapEx is reported as negative; convert to positive
                df["value"] = df["value"].abs()
                return df
        return pd.DataFrame(columns=["date", "value"])

    @staticmethod
    def _series_to_df(s: pd.Series) -> pd.DataFrame:
        """Convert a pandas Series (date index, numeric values) to standard DataFrame."""
        df = s.reset_index()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)

    # ── Chip Makers ───────────────────────────────────────────

    def nvidia_revenue(self) -> pd.DataFrame:
        """NVIDIA quarterly total revenue (USD). AI chip demand proxy."""
        return self._quarterly_revenue("NVDA")

    def nvidia_net_income(self) -> pd.DataFrame:
        """NVIDIA quarterly net income (USD). AI chip profitability."""
        return self._quarterly_net_income("NVDA")

    def tsmc_revenue(self) -> pd.DataFrame:
        """TSMC quarterly revenue (TWD). Global semiconductor demand proxy.
        TSMC manufactures chips for NVIDIA, AMD, Apple, Qualcomm — leading indicator for chip demand."""
        return self._quarterly_revenue("TSM")

    def tsmc_net_income(self) -> pd.DataFrame:
        """TSMC quarterly net income (TWD)."""
        return self._quarterly_net_income("TSM")

    def broadcom_revenue(self) -> pd.DataFrame:
        """Broadcom quarterly revenue (USD). Custom AI ASIC + networking chips."""
        return self._quarterly_revenue("AVGO")

    def asml_revenue(self) -> pd.DataFrame:
        """ASML quarterly revenue (EUR). Monopoly EUV lithography — upstream leading indicator.
        ASML bookings precede chip fab buildout by 12-18 months."""
        return self._quarterly_revenue("ASML")

    def asml_net_income(self) -> pd.DataFrame:
        """ASML quarterly net income (EUR)."""
        return self._quarterly_net_income("ASML")

    # ── Hyperscalers ──────────────────────────────────────────

    def microsoft_revenue(self) -> pd.DataFrame:
        """Microsoft quarterly total revenue (USD). Includes Azure cloud revenue."""
        return self._quarterly_revenue("MSFT")

    def microsoft_capex(self) -> pd.DataFrame:
        """Microsoft quarterly CapEx (USD). Data center + AI infrastructure investment.
        Azure cloud expansion, GPU cluster buildout spending."""
        return self._quarterly_capex("MSFT")

    def amazon_revenue(self) -> pd.DataFrame:
        """Amazon quarterly total revenue (USD). Includes AWS cloud revenue."""
        return self._quarterly_revenue("AMZN")

    def amazon_capex(self) -> pd.DataFrame:
        """Amazon quarterly CapEx (USD). Data center + logistics.
        AWS infrastructure expansion, largest hyperscale capex spender."""
        return self._quarterly_capex("AMZN")

    def google_revenue(self) -> pd.DataFrame:
        """Alphabet (Google) quarterly total revenue (USD). Includes GCP cloud revenue."""
        return self._quarterly_revenue("GOOGL")

    def google_capex(self) -> pd.DataFrame:
        """Alphabet (Google) quarterly CapEx (USD). Data center + AI infrastructure.
        TPU cluster buildout, GCP expansion, DeepMind compute infrastructure."""
        return self._quarterly_capex("GOOGL")

    def meta_revenue(self) -> pd.DataFrame:
        """Meta quarterly total revenue (USD)."""
        return self._quarterly_revenue("META")

    def meta_capex(self) -> pd.DataFrame:
        """Meta quarterly CapEx (USD). AI training clusters (600K+ GPUs).
        Open-source LLM infrastructure, Llama model training compute."""
        return self._quarterly_capex("META")

    # ── Aggregate ─────────────────────────────────────────────

    def hyperscaler_total_capex(self) -> pd.DataFrame:
        """Total quarterly CapEx: MSFT + AMZN + GOOGL + META (USD).
        Aggregate AI infrastructure spending — the most direct measure of AI buildout scale."""
        dfs = []
        for sym in ["MSFT", "AMZN", "GOOGL", "META"]:
            df = self._quarterly_capex(sym)
            if not df.empty:
                df = df.rename(columns={"value": sym})
                dfs.append(df)
        if not dfs:
            return pd.DataFrame(columns=["date", "value"])
        merged = dfs[0]
        for df in dfs[1:]:
            merged = pd.merge(merged, df, on="date", how="outer")
        merged = merged.sort_values("date")
        merged["value"] = merged[["MSFT", "AMZN", "GOOGL", "META"]].sum(axis=1)
        merged["value"] = merged["value"].round(0)
        return merged[["date", "value"]].dropna(subset=["value"]).reset_index(drop=True)

    def hyperscaler_total_revenue(self) -> pd.DataFrame:
        """Total quarterly revenue: MSFT + AMZN + GOOGL + META (USD).
        Aggregate cloud + AI platform revenue scale."""
        dfs = []
        for sym in ["MSFT", "AMZN", "GOOGL", "META"]:
            df = self._quarterly_revenue(sym)
            if not df.empty:
                df = df.rename(columns={"value": sym})
                dfs.append(df)
        if not dfs:
            return pd.DataFrame(columns=["date", "value"])
        merged = dfs[0]
        for df in dfs[1:]:
            merged = pd.merge(merged, df, on="date", how="outer")
        merged = merged.sort_values("date")
        merged["value"] = merged[["MSFT", "AMZN", "GOOGL", "META"]].sum(axis=1)
        merged["value"] = merged["value"].round(0)
        return merged[["date", "value"]].dropna(subset=["value"]).reset_index(drop=True)
