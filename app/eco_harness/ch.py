"""
Switzerland Macro Harness — AKShare (1.18.x compatible).

Normalizes all output to date/value DataFrame format.
Data from Jin10 financial calendar via AKShare.
"""

from __future__ import annotations

import pandas as pd


class CHHarness:
    """Swiss macroeconomic indicators via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not CHHarness._IMPORT_FAILED:
                    CHHarness._IMPORT_FAILED = True
                    print("[CHHarness] akshare not installed — pip install akshare")
                raise

    def cpi_yearly(self):
        """Switzerland CPI YoY (%) — quarterly."""
        self._init_ak()
        df = self._ak.macro_swiss_cpi_yearly()
        return _from_time_series(df)

    def gdp_quarterly(self):
        """Switzerland GDP QoQ (%) — quarterly."""
        self._init_ak()
        df = self._ak.macro_swiss_gdp_quarterly()
        return _from_time_series(df)

    def gdp_yearly(self):
        """Switzerland GDP YoY (%) — yearly."""
        self._init_ak()
        df = self._ak.macro_swiss_gbd_yearly()
        return _from_time_series(df)

    def bank_rate(self):
        """Switzerland SNB Policy Rate (%) — Swiss National Bank."""
        self._init_ak()
        df = self._ak.macro_swiss_gbd_bank_rate()
        return _from_time_series(df)

    def trade(self):
        """Switzerland Trade Balance."""
        self._init_ak()
        df = self._ak.macro_swiss_trade()
        return _from_time_series(df)

    def svme(self):
        """Switzerland SVME PMI — monthly."""
        self._init_ak()
        df = self._ak.macro_swiss_svme()
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
