"""
Global Economy Harness — World Bank + DBnomics.

Data limits:
  - World Bank: no key, no hard rate limit, ~50 requests/sec safe.
  - DBnomics: no key, no hard rate limit.
  - wbgapi caches metadata locally; first call per session is slow.
"""

import pandas as pd


class GlobalHarness:
    """World Bank WDI + DBnomics one-stop access."""

    def __init__(self):
        self._wb = None

    def _init_wb(self):
        if self._wb is None:
            import wbgapi as wb
            self._wb = wb

    # -- World Bank WDI --

    def gdp(self, country: str, mrv: int = 5, full: bool = False):
        """GDP (current USD) — NY.GDP.MKTP.CD. country='CHN','USA','JPN','WLD'"""
        self._init_wb()
        if full:
            return self._wb.data.DataFrame('NY.GDP.MKTP.CD', country, time=range(1960, 2026))
        return self._wb.data.DataFrame('NY.GDP.MKTP.CD', country, mrv=mrv)

    def gdp_per_capita(self, country: str, mrv: int = 5, full: bool = False):
        """GDP per capita (current USD) — NY.GDP.PCAP.CD"""
        self._init_wb()
        if full:
            return self._wb.data.DataFrame('NY.GDP.PCAP.CD', country, time=range(1960, 2026))
        return self._wb.data.DataFrame('NY.GDP.PCAP.CD', country, mrv=mrv)

    def gdp_growth(self, country: str, mrv: int = 5, full: bool = False):
        """GDP growth (annual %) — NY.GDP.MKTP.KD.ZG"""
        self._init_wb()
        if full:
            return self._wb.data.DataFrame('NY.GDP.MKTP.KD.ZG', country, time=range(1960, 2026))
        return self._wb.data.DataFrame('NY.GDP.MKTP.KD.ZG', country, mrv=mrv)

    def cpi(self, country: str, mrv: int = 5, full: bool = False):
        """CPI inflation (annual %) — FP.CPI.TOTL.ZG"""
        self._init_wb()
        if full:
            return self._wb.data.DataFrame('FP.CPI.TOTL.ZG', country, time=range(1960, 2026))
        return self._wb.data.DataFrame('FP.CPI.TOTL.ZG', country, mrv=mrv)

    def population(self, country: str, mrv: int = 5, full: bool = False):
        """Total population — SP.POP.TOTL"""
        self._init_wb()
        if full:
            return self._wb.data.DataFrame('SP.POP.TOTL', country, time=range(1960, 2026))
        return self._wb.data.DataFrame('SP.POP.TOTL', country, mrv=mrv)

    def trade_balance(self, country: str, mrv: int = 5, full: bool = False):
        """Trade balance % GDP — NE.RSB.GNFS.ZS"""
        self._init_wb()
        if full:
            return self._wb.data.DataFrame('NE.RSB.GNFS.ZS', country, time=range(1960, 2026))
        return self._wb.data.DataFrame('NE.RSB.GNFS.ZS', country, mrv=mrv)

    def get(self, indicator: str, country: str, mrv: int = 5):
        """Arbitrary WDI indicator by code. e.g. 'SL.UEM.TOTL.ZS' = unemployment."""
        self._init_wb()
        return self._wb.data.DataFrame(indicator, country, mrv=mrv)

    def search(self, query: str):
        """Search WDI indicators."""
        self._init_wb()
        return self._wb.series.info(q=query)

    # -- DBnomics --

    @staticmethod
    def dbnomics(provider: str, dataset: str, series: str = None):
        """Fetch from DBnomics (100+ providers: OECD, Eurostat, IMF, BIS...).

        Example:
            eh.global_.dbnomics('OECD', 'MEI', 'USA.B6BLTT01.CXCUSA.Q')
        """
        import dbnomics
        return dbnomics.fetch_series(provider, dataset, series)
