"""
UK Macro Harness — AKShare (1.18.x compatible).

Normalizes all output to date/value DataFrame format.
Data from Jin10 financial calendar via AKShare.
"""

from __future__ import annotations

import pandas as pd


class UKHarness:
    """UK macroeconomic indicators via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not UKHarness._IMPORT_FAILED:
                    UKHarness._IMPORT_FAILED = True
                    print("[UKHarness] akshare not installed — pip install akshare")
                raise

    def gdp_quarterly(self):
        """UK GDP QoQ (%) — quarterly."""
        self._init_ak()
        df = self._ak.macro_uk_gdp_quarterly()
        return _from_time_series(df)

    def gdp_yearly(self):
        """UK GDP YoY (%) — yearly."""
        self._init_ak()
        df = self._ak.macro_uk_gdp_yearly()
        return _from_time_series(df)

    def cpi_monthly(self):
        """UK CPI MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_uk_cpi_monthly()
        return _from_time_series(df)

    def cpi_yearly(self):
        """UK CPI YoY (%) — yearly."""
        self._init_ak()
        df = self._ak.macro_uk_cpi_yearly()
        return _from_time_series(df)

    def core_cpi_monthly(self):
        """UK Core CPI MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_uk_core_cpi_monthly()
        return _from_time_series(df)

    def core_cpi_yearly(self):
        """UK Core CPI YoY (%) — yearly."""
        self._init_ak()
        df = self._ak.macro_uk_core_cpi_yearly()
        return _from_time_series(df)

    def unemployment_rate(self):
        """UK Unemployment Rate (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_uk_unemployment_rate()
        return _from_time_series(df)

    def retail_monthly(self):
        """UK Retail Sales MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_uk_retail_monthly()
        return _from_time_series(df)

    def retail_yearly(self):
        """UK Retail Sales YoY (%) — yearly."""
        self._init_ak()
        df = self._ak.macro_uk_retail_yearly()
        return _from_time_series(df)

    def trade(self):
        """UK Trade Balance — monthly."""
        self._init_ak()
        df = self._ak.macro_uk_trade()
        return _from_time_series(df)

    def halifax_monthly(self):
        """UK Halifax House Price MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_uk_halifax_monthly()
        return _from_time_series(df)

    def halifax_yearly(self):
        """UK Halifax House Price YoY (%) — yearly."""
        self._init_ak()
        df = self._ak.macro_uk_halifax_yearly()
        return _from_time_series(df)

    def rightmove_monthly(self):
        """UK Rightmove House Price MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_uk_rightmove_monthly()
        return _from_time_series(df)

    def rightmove_yearly(self):
        """UK Rightmove House Price YoY (%) — yearly."""
        self._init_ak()
        df = self._ak.macro_uk_rightmove_yearly()
        return _from_time_series(df)

    def bank_rate(self):
        """UK Bank Rate (%) — Bank of England."""
        self._init_ak()
        df = self._ak.macro_uk_bank_rate()
        return _from_time_series(df)


def _from_time_series(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Jin10 time-series format: 时间, 前值, 现值, 发布日期."""
    df = df[["时间", "现值"]].copy()
    df.columns = ["date", "value"]
    df["date"] = _parse_date_series(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


def _parse_date_series(series: pd.Series) -> pd.Series:
    """Parse Chinese-format dates like '2026年05月', '2008第1季度'."""
    import re
    s = series.astype(str).str.strip()

    # Try standard parsing first
    try:
        result = pd.to_datetime(s)
        if result.notna().sum() > len(s) * 0.5:
            return result
    except Exception:
        pass

    # "2026年05月"
    try:
        result = pd.to_datetime(s, format="%Y年%m月", errors="coerce")
        if result.notna().sum() > len(s) * 0.5:
            return result
    except Exception:
        pass

    # "2008第1季度"
    def _parse_q(x):
        m = re.match(r"(\d{4})第(\d)季度", str(x))
        if m:
            y, q = int(m.group(1)), int(m.group(2))
            return f"{y}-{(q-1)*3+1:02d}-01"
        return None

    try:
        result = s.apply(_parse_q)
        result = pd.to_datetime(result)
        if result.notna().sum() > len(s) * 0.5:
            return result
    except Exception:
        pass

    return pd.to_datetime(s, errors="coerce")
