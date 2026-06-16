"""
Eco Data API Harness — unified macroeconomic data access layer.

Provides a single entry point for all major economic data sources:
  us/       FRED + US Treasury
  cn/       AKShare (China mainland)
  hk/       AKShare (Hong Kong)
  global/   World Bank + DBnomics
  sdmx/     OECD + ECB (via opensdmx)
  jp/       Bank of Japan + AKShare (Japan)
  euro/     AKShare (Eurozone)
  uk/       AKShare (United Kingdom)
  de/       AKShare (Germany)
  au/       AKShare (Australia)
  ca/       AKShare (Canada)
  ch/       AKShare (Switzerland)
  shipping/ AKShare (Baltic freight indices)
  banks/    AKShare (central bank policy rates)
  energy/   EIA

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
from app.eco_harness.euro import EuroHarness
from app.eco_harness.uk import UKHarness
from app.eco_harness.germany import GermanyHarness
from app.eco_harness.au import AUHarness
from app.eco_harness.ca import CAHarness
from app.eco_harness.ch import CHHarness
from app.eco_harness.shipping import ShippingHarness
from app.eco_harness.banks import BankRateHarness
from app.eco_harness.alternative import AlternativeHarness
from app.eco_harness.llm_metrics import LLMMetricsHarness
from app.eco_harness.defi_metrics import DeFiMetricsHarness
from app.eco_harness.ai_infra import AIInfraHarness
from app.eco_harness.ai_companies import AICompaniesHarness

try:
    from app.eco_harness.sdmx import SDMXHarness
    _HAS_SDMX = True
except ImportError:
    _HAS_SDMX = False


class EcoHarness:
    __slots__ = ('us', 'cn', 'hk', 'bond', 'futures', 'global_', 'sdmx',
                 'jp', 'euro', 'uk', 'de', 'au', 'ca', 'ch', 'shipping',
                 'banks', 'alt', 'llm', 'defi', 'energy', 'ai', 'ai_co')

    def __init__(self, fred_api_key: str = '', eia_api_key: str = ''):
        self.us = USHarness(fred_api_key)
        self.cn = CNHarness()
        self.hk = HKHarness()
        self.bond = BondHarness()
        self.futures = FuturesHarness()
        self.global_ = GlobalHarness()
        self.sdmx = SDMXHarness() if _HAS_SDMX else None
        self.jp = JPHarness()
        self.euro = EuroHarness()
        self.uk = UKHarness()
        self.de = GermanyHarness()
        self.au = AUHarness()
        self.ca = CAHarness()
        self.ch = CHHarness()
        self.shipping = ShippingHarness()
        self.banks = BankRateHarness()
        self.alt = AlternativeHarness()
        self.llm = LLMMetricsHarness()
        self.defi = DeFiMetricsHarness()
        self.energy = EnergyHarness(eia_api_key)
        self.ai = AIInfraHarness(fred_api_key)
        self.ai_co = AICompaniesHarness()

    @property
    def available_sources(self):
        sources = ['us', 'cn', 'hk', 'global_', 'jp', 'euro', 'uk', 'de',
                   'au', 'ca', 'ch', 'shipping', 'banks', 'alt', 'llm', 'defi', 'energy', 'ai', 'ai_co']
        if _HAS_SDMX:
            sources.append('sdmx')
        return sources

    def __repr__(self):
        status = 'sdmx' if _HAS_SDMX else 'no-sdmx'
        return f'EcoHarness(us/cn/hk/global_/euro/uk/de/jp/au/ca/ch/shipping/banks/{status}/energy)'
