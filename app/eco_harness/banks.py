"""
Central Bank Rates Harness — AKShare (1.18.x compatible).

Policy interest rates from major central banks worldwide.
Data from Jin10 financial calendar via AKShare.
"""

from __future__ import annotations

import pandas as pd


class BankRateHarness:
    """Global central bank policy rates via AKShare."""

    _IMPORT_FAILED = False

    # Map country codes to AKShare function names
    _BANKS = {
        "eu": ("macro_bank_euro_interest_rate", "ECB"),
        "uk": ("macro_bank_english_interest_rate", "BOE"),
        "jp": ("macro_bank_japan_interest_rate", "BOJ"),
        "au": ("macro_bank_australia_interest_rate", "RBA"),
        "ch": ("macro_bank_switzerland_interest_rate", "SNB"),
        "cn": ("macro_bank_china_interest_rate", "PBOC"),
        "us": ("macro_bank_usa_interest_rate", "Fed"),
        "in": ("macro_bank_india_interest_rate", "RBI"),
        "br": ("macro_bank_brazil_interest_rate", "BCB"),
        "nz": ("macro_bank_newzealand_interest_rate", "RBNZ"),
        "ru": ("macro_bank_russia_interest_rate", "CBR"),
    }

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not BankRateHarness._IMPORT_FAILED:
                    BankRateHarness._IMPORT_FAILED = True
                    print("[BankRateHarness] akshare not installed")
                raise

    def _get_bank_rate(self, func_name: str):
        self._init_ak()
        fn = getattr(self._ak, func_name)
        df = fn()
        return _from_calendar(df)

    def eu_rate(self):
        """ECB Main Refinancing Rate (%)."""
        return self._get_bank_rate("macro_bank_euro_interest_rate")

    def uk_rate(self):
        """BOE Bank Rate (%)."""
        return self._get_bank_rate("macro_bank_english_interest_rate")

    def jp_rate(self):
        """BOJ Policy Rate (%)."""
        return self._get_bank_rate("macro_bank_japan_interest_rate")

    def au_rate(self):
        """RBA Cash Rate (%)."""
        return self._get_bank_rate("macro_bank_australia_interest_rate")

    def ch_rate(self):
        """SNB Policy Rate (%)."""
        return self._get_bank_rate("macro_bank_switzerland_interest_rate")

    def cn_rate(self):
        """PBOC Benchmark Rate (%)."""
        return self._get_bank_rate("macro_bank_china_interest_rate")

    def us_rate(self):
        """Fed Funds Rate from AKShare (%)."""
        return self._get_bank_rate("macro_bank_usa_interest_rate")

    def in_rate(self):
        """RBI Repo Rate (%)."""
        return self._get_bank_rate("macro_bank_india_interest_rate")

    def br_rate(self):
        """BCB Selic Rate (%)."""
        return self._get_bank_rate("macro_bank_brazil_interest_rate")

    def nz_rate(self):
        """RBNZ OCR (%)."""
        return self._get_bank_rate("macro_bank_newzealand_interest_rate")

    def ru_rate(self):
        """CBR Key Rate (%)."""
        return self._get_bank_rate("macro_bank_russia_interest_rate")


def _from_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Jin10 financial calendar format: 商品, 日期, 今值, 预测值, 前值."""
    df = df[["日期", "今值"]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)
