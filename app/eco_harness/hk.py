"""
Hong Kong Macro Harness — AKShare.

Normalizes all output to date/value DataFrame format.
"""

from __future__ import annotations

import pandas as pd


class HKHarness:
    """Hong Kong macroeconomic indicators via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not HKHarness._IMPORT_FAILED:
                    HKHarness._IMPORT_FAILED = True
                    print("[HKHarness] akshare not installed — pip install akshare")
                raise

    # -- Core indicators --

    def cpi(self):
        """香港 CPI 月度同比"""
        self._init_ak()
        df = self._ak.macro_china_hk_cpi()
        return _from_financial_calendar(df)

    def ppi(self):
        """香港 PPI 季度同比"""
        self._init_ak()
        df = self._ak.macro_china_hk_ppi()
        return _from_financial_calendar(df)

    def gdp(self):
        """香港 GDP (季度, 百万港元)"""
        self._init_ak()
        df = self._ak.macro_china_hk_gbp()
        return _from_financial_calendar(df)

    def unemployment(self):
        """香港失业率 (%)"""
        self._init_ak()
        df = self._ak.macro_china_hk_rate_of_unemployment()
        return _from_financial_calendar(df)

    def trade_balance(self):
        """香港贸易差额 (亿港元)"""
        self._init_ak()
        df = self._ak.macro_china_hk_trade_diff_ratio()
        return _from_financial_calendar(df)

    def building_amount(self):
        """香港建造工程总值 (百万港元)"""
        self._init_ak()
        df = self._ak.macro_china_hk_building_amount()
        return _from_financial_calendar(df)

    def building_volume(self):
        """香港建造工程量"""
        self._init_ak()
        df = self._ak.macro_china_hk_building_volume()
        return _from_financial_calendar(df)

    def hibor_3m(self):
        """香港 3个月 HIBOR (%)"""
        self._init_ak()
        df = self._ak.macro_china_hk_market_info()
        df = df[["日期", "3M-定价"]].copy()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


def _from_financial_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize financial calendar format: 时间, 前值, 现值, 发布日期."""
    df = df[["时间", "现值"]].copy()
    df.columns = ["date_str", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = _parse_hk_date(df["date_str"])
    return df.dropna(subset=["value", "date"]).sort_values("date")[["date", "value"]].reset_index(drop=True)


def _parse_hk_date(series: pd.Series) -> pd.Series:
    """Parse HK dates: '2008年01月' → datetime, '2008第1季度' → 2008-01-01."""
    import re
    s = series.astype(str).str.strip()
    # Try standard parsing first
    try:
        result = pd.to_datetime(s, format="%Y年%m月", errors="coerce")
        if result.notna().sum() > len(s) * 0.5:
            return result
    except Exception:
        pass
    # Quarter: "2008第1季度"
    def _parse_q(v):
        m = re.match(r"(\d{4})第(\d)季度", v)
        if m:
            return pd.Timestamp(year=int(m.group(1)), month=(int(m.group(2)) - 1) * 3 + 1, day=1)
        return pd.NaT
    return s.apply(_parse_q)
