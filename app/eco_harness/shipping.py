"""
Shipping Indices Harness — AKShare (1.18.x compatible).

Global shipping indices: BDI, BCI, BPI, BCTI.
All from AKShare macro_shipping_* functions, sourced from sina finance.
Data available from 1988 to present.
"""

from __future__ import annotations

import pandas as pd


class ShippingHarness:
    """Global shipping / freight indices via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not ShippingHarness._IMPORT_FAILED:
                    ShippingHarness._IMPORT_FAILED = True
                    print("[ShippingHarness] akshare not installed")
                raise

    def bdi(self):
        """Baltic Dry Index — daily."""
        self._init_ak()
        df = self._ak.macro_shipping_bdi()
        return _from_shipping(df)

    def bci(self):
        """Baltic Capesize Index — daily."""
        self._init_ak()
        df = self._ak.macro_shipping_bci()
        return _from_shipping(df)

    def bpi(self):
        """Baltic Panamax Index — daily."""
        self._init_ak()
        df = self._ak.macro_shipping_bpi()
        return _from_shipping(df)

    def bcti(self):
        """Baltic Clean Tanker Index — daily."""
        self._init_ak()
        df = self._ak.macro_shipping_bcti()
        return _from_shipping(df)


def _from_shipping(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize shipping index format: 日期, 最新值, ..."""
    df = df[["日期", "最新值"]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)
