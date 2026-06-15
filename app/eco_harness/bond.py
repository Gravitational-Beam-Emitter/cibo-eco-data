"""
Bond Market Harness — AKShare.

Normalizes all output to date/value DataFrame format.
Covers: China/US government bond yields, credit spreads, convertible bonds.
"""

from __future__ import annotations

import pandas as pd


class BondHarness:
    """Bond market data via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not BondHarness._IMPORT_FAILED:
                    BondHarness._IMPORT_FAILED = True
                    print("[BondHarness] akshare not installed — pip install akshare")
                raise

    # -- China/US yield comparison (bond_zh_us_rate) --

    def cn_yield_2y(self):
        """中国2年期国债收益率 (%)"""
        return self._yield_series("中国国债收益率2年")

    def cn_yield_5y(self):
        """中国5年期国债收益率 (%)"""
        return self._yield_series("中国国债收益率5年")

    def cn_yield_30y(self):
        """中国30年期国债收益率 (%)"""
        return self._yield_series("中国国债收益率30年")

    def cn_yield_10y_2y_spread(self):
        """中国10年-2年国债利差 (%)"""
        return self._yield_series("中国国债收益率10年-2年")

    def us_yield_2y(self):
        """美国2年期国债收益率 (%)"""
        return self._yield_series("美国国债收益率2年")

    def us_yield_5y(self):
        """美国5年期国债收益率 (%)"""
        return self._yield_series("美国国债收益率5年")

    def us_yield_30y(self):
        """美国30年期国债收益率 (%)"""
        return self._yield_series("美国国债收益率30年")

    def us_yield_10y_2y_spread(self):
        """美国10年-2年国债利差 (%)"""
        return self._yield_series("美国国债收益率10年-2年")

    def _yield_series(self, column: str) -> pd.DataFrame:
        self._init_ak()
        df = self._ak.bond_zh_us_rate()
        df = df[["日期", column]].copy()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)

    # -- Convertible bonds --

    def cb_index(self):
        """可转债等权指数"""
        self._init_ak()
        df = self._ak.bond_cb_index_jsl()
        df = df[["price_dt", "price"]].copy()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


class FuturesHarness:
    """Futures market data via AKShare (sina source)."""

    _IMPORT_FAILED = False
    _CONTRACTS = {
        "AU0": "沪金主力",
        "AG0": "沪银主力",
        "CU0": "沪铜主力",
        "AL0": "沪铝主力",
        "RB0": "螺纹钢主力",
        "I0":  "铁矿石主力",
        "SC0": "原油主力",
        "RU0": "橡胶主力",
        "M0":  "豆粕主力",
        "Y0":  "豆油主力",
    }

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not FuturesHarness._IMPORT_FAILED:
                    FuturesHarness._IMPORT_FAILED = True
                    print("[FuturesHarness] akshare not installed")
                raise

    def _futures_series(self, symbol: str) -> pd.DataFrame:
        self._init_ak()
        df = self._ak.futures_main_sina(symbol=symbol)
        df = df[["日期", "收盘价"]].copy()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)

    def gold_futures(self):
        """沪金主力连续 (AU0) 收盘价"""
        return self._futures_series("AU0")

    def silver_futures(self):
        """沪银主力连续 (AG0) 收盘价"""
        return self._futures_series("AG0")

    def copper_futures(self):
        """沪铜主力连续 (CU0) 收盘价"""
        return self._futures_series("CU0")

    def rebar_futures(self):
        """螺纹钢主力连续 (RB0) 收盘价"""
        return self._futures_series("RB0")

    def iron_ore_futures(self):
        """铁矿石主力连续 (I0) 收盘价"""
        return self._futures_series("I0")

    def crude_futures(self):
        """上海原油主力连续 (SC0) 收盘价"""
        return self._futures_series("SC0")
