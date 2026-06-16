"""
Japan Macro Harness — boj-api + AKShare.

Data limits:
  - boj-api: Max 250 series / 60,000 data points per request (auto-paginated).
    No API key. Public since 2026-02-18. Date format: YYYYMM.
  - AKShare: Jin10 financial calendar data, rate varies by endpoint.
"""

from __future__ import annotations

import pandas as pd


class JPHarness:
    """Japan macroeconomic indicators via boj-api and AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._client = None
        self._Database = None
        self._ak = None

    # -- boj-api --

    def _init(self):
        if self._client is None:
            try:
                from boj_api import BOJClient, Database
                self._BOJClient = BOJClient
                self._Database = Database
                self._client = BOJClient()
            except ImportError:
                print("[JPHarness] boj-api not installed — pip install boj-api")
                raise

    def _get(self, db, codes: list, start: str = "201501", end: str = None):
        self._init()
        if end is None:
            from datetime import datetime
            end = datetime.now().strftime("%Y%m")
        try:
            resp = self._client.get_data_by_code(
                db=db, code=codes, start_date=start, end_date=end
            )
        except Exception as e:
            print(f"[JPHarness] API error for {codes}: {e}")
            return pd.DataFrame(columns=["date", "value"])

        records = []
        for s in resp.series:
            for obs in s.observations:
                records.append({"code": s.code, "date": obs.date, "value": obs.value})
        return pd.DataFrame(records)

    def fx(self, pair: str = "USDJPY", start: str = "201501", end: str = None):
        """Get FX rate from BoJ."""
        self._init()
        return self._get(self._Database.FM08, [pair], start, end)

    def tankan(self, start: str = "201501", end: str = None):
        """Tankan survey (短观) from BoJ."""
        self._init()
        return self._get(self._Database.CO, ["CO1"], start, end)

    def get(self, db, codes: list, start: str = "201501", end: str = None):
        """Arbitrary BOJ series. See Database enum for available DBs."""
        return self._get(db, codes, start, end)

    # -- AKShare (Jin10) --

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not JPHarness._IMPORT_FAILED:
                    JPHarness._IMPORT_FAILED = True
                    print("[JPHarness] akshare not installed — pip install akshare")
                raise

    def cpi_yearly(self):
        """Japan CPI YoY (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_japan_cpi_yearly()
        return _from_time_series(df)

    def core_cpi_yearly(self):
        """Japan Core CPI YoY (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_japan_core_cpi_yearly()
        return _from_time_series(df)

    def unemployment_rate(self):
        """Japan Unemployment Rate (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_japan_unemployment_rate()
        return _from_time_series(df)

    def bank_rate(self):
        """Japan Policy Rate (%) — Bank of Japan."""
        self._init_ak()
        df = self._ak.macro_japan_bank_rate()
        return _from_time_series(df)

    def head_indicator(self):
        """Japan Leading Indicator."""
        self._init_ak()
        df = self._ak.macro_japan_head_indicator()
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
