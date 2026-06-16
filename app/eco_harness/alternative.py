"""
Alternative & Forward-Looking Indicators Harness — AKShare (1.18.x compatible).

Forward-looking / non-traditional macro data:
  - Semiconductor index (SOX) — tech cycle leads economic cycle
  - Shipping indices (BDTI dirty tanker)
  - Commodity indices (China commodity, energy, agricultural, construction)
  - ETF holdings (gold/silver sentiment)
  - Consumer sentiment (Michigan)
  - Market risk indicators
"""

from __future__ import annotations

import pandas as pd


class AlternativeHarness:
    """Alternative and forward-looking macro indicators via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not AlternativeHarness._IMPORT_FAILED:
                    AlternativeHarness._IMPORT_FAILED = True
                    print("[AlternativeHarness] akshare not installed")
                raise

    # -- Technology & Innovation (leading indicators) --

    def sox_index(self):
        """Philadelphia Semiconductor Index (SOX) — daily.
        Semiconductors are a 6-12 month leading indicator for global economy."""
        self._init_ak()
        df = self._ak.macro_global_sox_index()
        return _from_index(df)

    # -- Shipping & Supply Chain --

    def bdti(self):
        """Baltic Dirty Tanker Index — daily.
        Crude oil tanker freight rates, complements BDI/BCI/BPI/BCTI."""
        self._init_ak()
        df = self._ak.macro_china_bdti_index()
        return _from_index(df)

    # -- Commodity Indices (real-time industrial pulse) --

    def china_commodity_index(self):
        """China Commodity Price Index — daily.
        Broad commodity price indicator from China's markets."""
        self._init_ak()
        df = self._ak.macro_china_commodity_price_index()
        return _from_index(df)

    def china_energy_index(self):
        """China Energy Index — daily.
        Real-time energy sector indicator."""
        self._init_ak()
        df = self._ak.macro_china_energy_index()
        return _from_index(df)

    def china_agricultural_index(self):
        """China Agricultural Index — daily.
        Agricultural commodity prices, food inflation proxy."""
        self._init_ak()
        df = self._ak.macro_china_agricultural_index()
        return _from_index(df)

    def china_construction_index(self):
        """China Construction Index — daily.
        Construction material prices, real estate/infrastructure proxy."""
        self._init_ak()
        df = self._ak.macro_china_construction_index()
        return _from_index(df)

    # -- ETF Holdings (investor sentiment proxy) --

    def gold_etf_holdings(self):
        """Gold ETF Holdings — daily.
        Total gold ETF inventory + daily change. Safe-haven demand indicator."""
        self._init_ak()
        df = self._ak.macro_cons_gold()
        return _from_etf(df)

    def silver_etf_holdings(self):
        """Silver ETF Holdings — daily.
        Silver ETF inventory + daily change. Industrial + precious demand."""
        self._init_ak()
        df = self._ak.macro_cons_silver()
        return _from_etf(df)

    # -- Consumer Sentiment (forward-looking) --

    def michigan_sentiment(self):
        """US Michigan Consumer Sentiment — monthly.
        Forward-looking consumer confidence indicator."""
        self._init_ak()
        df = self._ak.macro_usa_michigan_consumer_sentiment()
        return _from_calendar(df)

    # -- OPEC Production --

    def opec_production(self):
        """OPEC Monthly Production — monthly.
        Aggregated OPEC crude oil production (10k barrels)."""
        self._init_ak()
        df = self._ak.macro_cons_opec_month()
        # Sum all country columns except date to get total OPEC production
        date_col = "日期"
        prod_cols = [c for c in df.columns if c != date_col]
        df["value"] = df[prod_cols].sum(axis=1, numeric_only=True)
        df["date"] = pd.to_datetime(df[date_col])
        df = df[["date", "value"]].dropna(subset=["value"]).sort_values("date")
        return df.reset_index(drop=True)


def _from_index(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize index format: 日期, 最新值, ..."""
    df = df[["日期", "最新值"]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


def _from_etf(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize ETF holdings format: 商品, 日期, 总库存, ..."""
    df = df[["日期", "总库存"]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


def _from_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Jin10 financial calendar format: 商品, 日期, 今值, 预测值, 前值."""
    df = df[["日期", "今值"]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)
