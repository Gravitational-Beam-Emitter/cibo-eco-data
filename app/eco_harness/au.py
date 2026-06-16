"""
Australia Macro Harness — AKShare (1.18.x compatible).

Normalizes all output to date/value DataFrame format.
Data from Jin10 financial calendar via AKShare.
"""

from __future__ import annotations

import pandas as pd


class AUHarness:
    """Australian macroeconomic indicators via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not AUHarness._IMPORT_FAILED:
                    AUHarness._IMPORT_FAILED = True
                    print("[AUHarness] akshare not installed — pip install akshare")
                raise

    def cpi_quarterly(self):
        """Australia CPI QoQ (%) — quarterly."""
        self._init_ak()
        df = self._ak.macro_australia_cpi_quarterly()
        return _from_time_series(df)

    def cpi_yearly(self):
        """Australia CPI YoY (%) — quarterly."""
        self._init_ak()
        df = self._ak.macro_australia_cpi_yearly()
        return _from_time_series(df)

    def ppi_quarterly(self):
        """Australia PPI QoQ (%) — quarterly."""
        self._init_ak()
        df = self._ak.macro_australia_ppi_quarterly()
        return _from_time_series(df)

    def unemployment_rate(self):
        """Australia Unemployment Rate (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_australia_unemployment_rate()
        return _from_time_series(df)

    def retail_rate_monthly(self):
        """Australia Retail Sales MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_australia_retail_rate_monthly()
        return _from_time_series(df)

    def trade(self):
        """Australia Trade Balance — monthly."""
        self._init_ak()
        df = self._ak.macro_australia_trade()
        return _from_time_series(df)

    def bank_rate(self):
        """Australia RBA Cash Rate (%) — Reserve Bank of Australia."""
        self._init_ak()
        df = self._ak.macro_australia_bank_rate()
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
    try:
        result = pd.to_datetime(s)
        if result.notna().sum() > len(s) * 0.5:
            return result
    except Exception:
        pass
    try:
        result = pd.to_datetime(s, format="%Y年%m月", errors="coerce")
        if result.notna().sum() > len(s) * 0.5:
            return result
    except Exception:
        pass
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
