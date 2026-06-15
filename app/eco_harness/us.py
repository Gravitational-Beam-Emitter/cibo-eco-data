"""
US Macro Harness — FRED + US Treasury.

Data limits: FRED free tier = 120 req/min, Treasury = no limit.
Date format: YYYY-MM-DD (FRED), flexible (Treasury).
"""

import pandas as pd
import requests

_FRED_SERIES = {
    'gdp':           'GDP',           # Billions of Dollars, Quarterly, SAAR
    'gdp_real':      'GDPC1',         # Real GDP, Quarterly
    'cpi':           'CPIAUCSL',      # CPI All Urban, Monthly, 1982-84=100
    'core_cpi':      'CPILFESL',      # CPI ex Food & Energy, Monthly
    'unemployment':  'UNRATE',        # Unemployment Rate %, Monthly
    'nonfarm':       'PAYEMS',        # Nonfarm Payrolls, Monthly
    'fed_funds':     'FEDFUNDS',      # Fed Funds Rate %, Monthly
    'treasury_10y':  'DGS10',         # 10Y Treasury %, Daily
    'treasury_2y':   'DGS2',          # 2Y Treasury %, Daily
    'treasury_3m':   'DTB3',          # 3M T-Bill %, Daily
    'mortgage_30y':  'MORTGAGE30US',  # 30Y Fixed Mortgage %, Weekly
    'ism_mfg':       None,            # NAPM discontinued — use search('ISM') or get() for latest
    'retail_sales':  'RSXFSN',        # Retail Sales, Monthly
    'industrial':    'INDPRO',        # Industrial Production, Monthly
    'trade_balance': 'BOPGSTB',       # Trade Balance, Monthly
    'm2':            'M2SL',          # M2 Money Supply, Monthly
    'deficit_pct':   'FYFSGDA188S',   # Federal Deficit % GDP, Annual
    'debt_gdp':      'GFDEGDQ188S',   # Federal Debt % GDP, Quarterly
}


class USHarness:
    def __init__(self, api_key: str):
        self._fred_key = api_key
        self._fred = None

    def _init_fred(self):
        if self._fred is None:
            from fredapi import Fred
            self._fred = Fred(api_key=self._fred_key)

    def _get_fred(self, code: str, start: str = None, end: str = None):
        self._init_fred()
        kwargs = {}
        if start:
            kwargs['observation_start'] = start
        if end:
            kwargs['observation_end'] = end
        s = self._fred.get_series(code, **kwargs)
        return s.reset_index().pipe(
            lambda df: df.rename(columns={'index': 'date', 0: 'value'})
        )

    # -- Core indicators (one method per, for discoverability) --

    def gdp(self, start=None, end=None):
        """Quarterly GDP (Billions, SAAR)"""
        return self._get_fred('GDP', start, end)

    def cpi(self, start=None, end=None):
        """Monthly CPI (1982-84=100)"""
        return self._get_fred('CPIAUCSL', start, end)

    def core_cpi(self, start=None, end=None):
        """Monthly Core CPI (ex Food & Energy)"""
        return self._get_fred('CPILFESL', start, end)

    def unemployment(self, start=None, end=None):
        """Monthly Unemployment Rate (%)"""
        return self._get_fred('UNRATE', start, end)

    def nonfarm(self, start=None, end=None):
        """Monthly Nonfarm Payrolls (thousands)"""
        return self._get_fred('PAYEMS', start, end)

    def fed_funds(self, start=None, end=None):
        """Monthly Fed Funds Rate (%)"""
        return self._get_fred('FEDFUNDS', start, end)

    def treasury_10y(self, start=None, end=None):
        """Daily 10Y Treasury Yield (%)"""
        return self._get_fred('DGS10', start, end)

    def treasury_2y(self, start=None, end=None):
        """Daily 2Y Treasury Yield (%)"""
        return self._get_fred('DGS2', start, end)

    def ism_mfg(self, start=None, end=None):
        """ISM Manufacturing PMI — NAPM was discontinued from FRED.
        Use eh.us.search('manufacturing pmi') to find current series,
        or eh.us.industrial() for Industrial Production as proxy."""
        return self.industrial(start, end)

    def m2(self, start=None, end=None):
        """Monthly M2 Money Supply"""
        return self._get_fred('M2SL', start, end)

    def retail_sales(self, start=None, end=None):
        """Monthly Retail Sales"""
        return self._get_fred('RSXFSN', start, end)

    def industrial(self, start=None, end=None):
        """Monthly Industrial Production Index"""
        return self._get_fred('INDPRO', start, end)

    def trade_balance(self, start=None, end=None):
        """Monthly Trade Balance"""
        return self._get_fred('BOPGSTB', start, end)

    def debt_gdp(self, start=None, end=None):
        """Quarterly Federal Debt % GDP"""
        return self._get_fred('GFDEGDQ188S', start, end)

    # -- Arbitrary series lookup --

    def get(self, code: str, start=None, end=None):
        """Fetch any FRED series by code (e.g. 'T10Y2Y', 'VIXCLS', 'TEDRATE')"""
        return self._get_fred(code, start, end)

    def search(self, query: str, limit: int = 10):
        """Search FRED for series"""
        self._init_fred()
        return self._fred.search(query).head(limit)[['id', 'title', 'frequency', 'units']]

    # -- US Treasury (no API key needed) --

    @staticmethod
    def treasury_debt_latest():
        """Latest total public debt from fiscaldata.treasury.gov"""
        resp = requests.get(
            'https://api.fiscaldata.treasury.gov/services/api/fiscal_service'
            '/v2/accounting/od/debt_to_penny',
            params={'sort': '-record_date', 'page[size]': 1}, timeout=15
        )
        data = resp.json()['data'][0]
        return float(data['tot_pub_debt_out_amt'])

    @staticmethod
    def treasury_rates_of_exchange(country: str = 'China', start: str = '2020-01-01'):
        """Get USD/foreign exchange rates. country='China' returns CNY/USD."""
        resp = requests.get(
            'https://api.fiscaldata.treasury.gov/services/api/fiscal_service'
            '/v1/accounting/od/rates_of_exchange',
            params={
                'filter': f'country:eq:{country},record_date:gte:{start}',
                'sort': 'record_date',
                'page[size]': 10000,
            }, timeout=30
        )
        df = pd.DataFrame(resp.json()['data'])
        df['record_date'] = pd.to_datetime(df['record_date'])
        df['exchange_rate'] = df['exchange_rate'].astype(float)
        return df[['record_date', 'currency', 'exchange_rate']]

    @staticmethod
    def treasury_avg_interest_rates(start: str = '2020-01-01'):
        """Average interest rates on US debt."""
        resp = requests.get(
            'https://api.fiscaldata.treasury.gov/services/api/fiscal_service'
            '/v2/accounting/od/avg_interest_rates',
            params={
                'filter': f'record_date:gte:{start}',
                'sort': 'record_date',
                'page[size]': 10000,
            }, timeout=30
        )
        df = pd.DataFrame(resp.json()['data'])
        df['record_date'] = pd.to_datetime(df['record_date'])
        df['avg_interest_rate_amt'] = df['avg_interest_rate_amt'].astype(float)
        return df[['record_date', 'avg_interest_rate_amt', 'security_type_desc']]
