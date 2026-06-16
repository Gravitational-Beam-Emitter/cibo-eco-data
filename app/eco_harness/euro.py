"""
Eurozone Macro Harness — AKShare (1.18.x compatible).

Normalizes all output to date/value DataFrame format.
Data from Jin10 financial calendar via AKShare.
"""

from __future__ import annotations

import pandas as pd


class EuroHarness:
    """Eurozone macroeconomic indicators via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not EuroHarness._IMPORT_FAILED:
                    EuroHarness._IMPORT_FAILED = True
                    print("[EuroHarness] akshare not installed — pip install akshare")
                raise

    def gdp_yoy(self):
        """Eurozone GDP YoY (%) — quarterly."""
        self._init_ak()
        df = self._ak.macro_euro_gdp_yoy()
        return _from_calendar(df)

    def cpi_yoy(self):
        """Eurozone CPI YoY (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_cpi_yoy()
        return _from_calendar(df)

    def cpi_mom(self):
        """Eurozone CPI MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_cpi_mom()
        return _from_calendar(df)

    def ppi_mom(self):
        """Eurozone PPI MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_ppi_mom()
        return _from_calendar(df)

    def manufacturing_pmi(self):
        """Eurozone Manufacturing PMI — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_manufacturing_pmi()
        return _from_calendar(df)

    def services_pmi(self):
        """Eurozone Services PMI — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_services_pmi()
        return _from_calendar(df)

    def unemployment_rate(self):
        """Eurozone Unemployment Rate (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_unemployment_rate_mom()
        return _from_calendar(df)

    def industrial_production_mom(self):
        """Eurozone Industrial Production MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_industrial_production_mom()
        return _from_calendar(df)

    def retail_sales_mom(self):
        """Eurozone Retail Sales MoM (%) — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_retail_sales_mom()
        return _from_calendar(df)

    def trade_balance(self):
        """Eurozone Trade Balance — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_trade_balance()
        return _from_calendar(df)

    def sentix_confidence(self):
        """Eurozone Sentix Investor Confidence — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_sentix_investor_confidence()
        return _from_calendar(df)

    def zew_sentiment(self):
        """Eurozone ZEW Economic Sentiment — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_zew_economic_sentiment()
        return _from_calendar(df)

    def current_account(self):
        """Eurozone Current Account MoM — monthly."""
        self._init_ak()
        df = self._ak.macro_euro_current_account_mom()
        return _from_calendar(df)

    def employment_change_qoq(self):
        """Eurozone Employment Change QoQ (%) — quarterly."""
        self._init_ak()
        df = self._ak.macro_euro_employment_change_qoq()
        return _from_calendar(df)

    # -- LME metals (Eurozone-related) --
    def lme_holding(self):
        """LME Metal Holdings."""
        self._init_ak()
        df = self._ak.macro_euro_lme_holding()
        return _from_calendar(df)

    def lme_stock(self):
        """LME Metal Stocks."""
        self._init_ak()
        df = self._ak.macro_euro_lme_stock()
        return _from_calendar(df)


def _from_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Jin10 financial calendar format: 商品, 日期, 今值, 预测值, 前值."""
    df = df[["日期", "今值"]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)
