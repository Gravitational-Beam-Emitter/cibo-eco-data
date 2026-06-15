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
from app.eco_harness.global_ import GlobalHarness
from app.eco_harness.sdmx import SDMXHarness
from app.eco_harness.jp import JPHarness
from app.eco_harness.energy import EnergyHarness


class EcoHarness:
    __slots__ = ('us', 'cn', 'global_', 'sdmx', 'jp', 'energy')

    def __init__(self, fred_api_key: str = '', eia_api_key: str = ''):
        self.us = USHarness(fred_api_key)
        self.cn = CNHarness()
        self.global_ = GlobalHarness()
        self.sdmx = SDMXHarness()
        self.jp = JPHarness()
        self.energy = EnergyHarness(eia_api_key)

    def __repr__(self):
        return 'EcoHarness(us/cn/global_/sdmx/jp/energy)'
