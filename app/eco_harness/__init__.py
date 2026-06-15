"""
Eco Data API Harness — unified macroeconomic data access layer.

Provides a single entry point for all major economic data sources:
  us/      FRED + US Treasury
  cn/      AKShare
  global/  World Bank + DBnomics
  sdmx/    OECD + ECB (via opensdmx)
  jp/      Bank of Japan
  energy/  EIA

Usage:
    from app.eco_harness import EcoHarness
    eh = EcoHarness(fred_api_key='...')
    df = eh.us.gdp()
    df = eh.cn.cpi()
    df = eh.global.gdp('CHN')
"""

from app.eco_harness.us import USHarness
from app.eco_harness.cn import CNHarness
from app.eco_harness.hk import HKHarness
from app.eco_harness.bond import BondHarness, FuturesHarness
from app.eco_harness.global_ import GlobalHarness
from app.eco_harness.jp import JPHarness
from app.eco_harness.energy import EnergyHarness

try:
    from app.eco_harness.sdmx import SDMXHarness
    _HAS_SDMX = True
except ImportError:
    _HAS_SDMX = False


class EcoHarness:
    __slots__ = ('us', 'cn', 'hk', 'bond', 'futures', 'global_', 'sdmx', 'jp', 'energy')

    def __init__(self, fred_api_key: str = '', eia_api_key: str = ''):
        self.us = USHarness(fred_api_key)
        self.cn = CNHarness()
        self.hk = HKHarness()
        self.bond = BondHarness()
        self.futures = FuturesHarness()
        self.global_ = GlobalHarness()
        self.sdmx = SDMXHarness() if _HAS_SDMX else None
        self.jp = JPHarness()
        self.energy = EnergyHarness(eia_api_key)

    @property
    def available_sources(self):
        sources = ['us', 'cn', 'hk', 'global_', 'jp', 'energy']
        if _HAS_SDMX:
            sources.append('sdmx')
        return sources

    def __repr__(self):
        status = 'sdmx' if _HAS_SDMX else 'no-sdmx'
        return f'EcoHarness(us/cn/hk/global_/{status}/jp/energy)'
