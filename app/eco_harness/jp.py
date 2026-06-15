"""
Bank of Japan Harness — boj-api.

Data limits:
  - Max 250 series / 60,000 data points per request (auto-paginated).
  - No API key. Public since 2026-02-18.
  - Date format: YYYYMM (not YYYYMMDD!).

NOTE: Series codes must match what the current boj-api version expects.
Use client.get_metadata(db) to discover available series codes.
"""

from __future__ import annotations

import pandas as pd


class JPHarness:
    """Bank of Japan statistics via boj-api."""

    def __init__(self):
        self._client = None
        self._Database = None

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
        """Get FX rate. NOTE: series codes may differ from pair name.
        Use get_metadata to discover available codes."""
        self._init()
        return self._get(self._Database.FM08, [pair], start, end)

    def tankan(self, start: str = "201501", end: str = None):
        """Tankan survey (短观)."""
        self._init()
        return self._get(self._Database.CO, ["CO1"], start, end)

    def get(self, db, codes: list, start: str = "201501", end: str = None):
        """Arbitrary BOJ series. See Database enum for available DBs."""
        return self._get(db, codes, start, end)
