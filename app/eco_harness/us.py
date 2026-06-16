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

    # -- FRED Global Exchange Rates --

    def fx_china(self, start=None, end=None):
        """USD/CNY exchange rate (FRED: DEXCHUS)."""
        return self._get_fred('DEXCHUS', start, end)

    def fx_japan(self, start=None, end=None):
        """USD/JPY exchange rate (FRED: DEXJPUS)."""
        return self._get_fred('DEXJPUS', start, end)

    def fx_euro(self, start=None, end=None):
        """USD/EUR exchange rate (FRED: DEXUSEU)."""
        return self._get_fred('DEXUSEU', start, end)

    def fx_uk(self, start=None, end=None):
        """USD/GBP exchange rate (FRED: DEXUSUK)."""
        return self._get_fred('DEXUSUK', start, end)

    def fx_canada(self, start=None, end=None):
        """USD/CAD exchange rate (FRED: DEXCAUS)."""
        return self._get_fred('DEXCAUS', start, end)

    def fx_australia(self, start=None, end=None):
        """USD/AUD exchange rate (FRED: DEXUSAL)."""
        return self._get_fred('DEXUSAL', start, end)

    def fx_korea(self, start=None, end=None):
        """USD/KRW exchange rate (FRED: DEXKOUS)."""
        return self._get_fred('DEXKOUS', start, end)

    def fx_india(self, start=None, end=None):
        """USD/INR exchange rate (FRED: DEXINUS)."""
        return self._get_fred('DEXINUS', start, end)

    def fx_brazil(self, start=None, end=None):
        """USD/BRL exchange rate (FRED: DEXBZUS)."""
        return self._get_fred('DEXBZUS', start, end)

    def vix(self, start=None, end=None):
        """CBOE Volatility Index — VIX (FRED: VIXCLS)."""
        return self._get_fred('VIXCLS', start, end)

    def yield_10y2y_spread(self, start=None, end=None):
        """10Y-2Y Treasury spread (FRED: T10Y2Y)."""
        return self._get_fred('T10Y2Y', start, end)

    def yield_10y3m_spread(self, start=None, end=None):
        """10Y-3M Treasury spread (FRED: T10Y3M)."""
        return self._get_fred('T10Y3M', start, end)

    # -- FRED Global Policy Rates (more reliable than Jin10) --

    def policy_rate_ecb(self, start=None, end=None):
        """ECB Deposit Facility Rate (FRED: ECBDFR)."""
        return self._get_fred('ECBDFR', start, end)

    def policy_rate_boe(self, start=None, end=None):
        """BOE Bank Rate (FRED: BOERUKQDS)."""
        return self._get_fred('BOERUKQDS', start, end)

    def policy_rate_boj(self, start=None, end=None):
        """BOJ Policy Rate (FRED: JPNPRATE)."""
        return self._get_fred('JPNPRATE', start, end)

    def policy_rate_rba(self, start=None, end=None):
        """RBA Cash Rate Target (FRED: RBATCTR)."""
        return self._get_fred('RBATCTR', start, end)

    def policy_rate_snb(self, start=None, end=None):
        """SNB Policy Rate (FRED: CHEPRATE)."""
        return self._get_fred('CHEPRATE', start, end)

    def policy_rate_boc(self, start=None, end=None):
        """BoC Policy Rate (FRED: CAPRATE)."""
        return self._get_fred('CAPRATE', start, end)

    def policy_rate_rbnz(self, start=None, end=None):
        """RBNZ Official Cash Rate (FRED: NZLPRATE)."""
        return self._get_fred('NZLPRATE', start, end)

    def policy_rate_rbi(self, start=None, end=None):
        """RBI Repo Rate (FRED: INDPRATE)."""
        return self._get_fred('INDPRATE', start, end)

    def policy_rate_bcb(self, start=None, end=None):
        """BCB Selic Rate (FRED: BRALRTA)."""
        return self._get_fred('BRALRTA', start, end)

    # -- Credit Spreads (FRED) -- risk appetite & stress gauges --

    def credit_spread_baa(self, start=None, end=None):
        """Moody's Baa - 10Y Treasury spread (FRED: BAA10Y)."""
        return self._get_fred('BAA10Y', start, end)

    def credit_spread_aaa(self, start=None, end=None):
        """Moody's Aaa - 10Y Treasury spread (FRED: AAA10Y)."""
        return self._get_fred('AAA10Y', start, end)

    def credit_spread_hy(self, start=None, end=None):
        """ICE BofA US High Yield OAS (FRED: BAMLH0A0HYM2)."""
        return self._get_fred('BAMLH0A0HYM2', start, end)

    def ted_spread(self, start=None, end=None):
        """TED Spread — 3M LIBOR - 3M T-Bill (FRED: TEDRATE). Stale since 2022."""
        return self._get_fred('TEDRATE', start, end)

    # -- Housing (FRED) --

    def housing_starts(self, start=None, end=None):
        """Housing Starts: Total (FRED: HOUST)."""
        return self._get_fred('HOUST', start, end)

    def building_permits(self, start=None, end=None):
        """Building Permits: Total (FRED: PERMIT)."""
        return self._get_fred('PERMIT', start, end)

    def case_shiller(self, start=None, end=None):
        """S&P/Case-Shiller US Home Price Index (FRED: CSUSHPINSA)."""
        return self._get_fred('CSUSHPINSA', start, end)

    # -- Labor Market Detail (FRED) --

    def labor_force_participation(self, start=None, end=None):
        """Labor Force Participation Rate % (FRED: CIVPART)."""
        return self._get_fred('CIVPART', start, end)

    def job_openings(self, start=None, end=None):
        """Job Openings: Total Nonfarm (FRED: JTSJOL)."""
        return self._get_fred('JTSJOL', start, end)

    def avg_hourly_earnings(self, start=None, end=None):
        """Average Hourly Earnings of All Employees (FRED: AHETPI)."""
        return self._get_fred('AHETPI', start, end)

    def u6_unemployment(self, start=None, end=None):
        """U6 Unemployment Rate — broader measure (FRED: U6RATE)."""
        return self._get_fred('U6RATE', start, end)

    # -- PCE Inflation — Fed's preferred gauge (FRED) --

    def pce(self, start=None, end=None):
        """Personal Consumption Expenditures (FRED: PCE)."""
        return self._get_fred('PCE', start, end)

    def core_pce(self, start=None, end=None):
        """Core PCE ex Food & Energy (FRED: PCEPILFE)."""
        return self._get_fred('PCEPILFE', start, end)

    def ppi_all_commodities(self, start=None, end=None):
        """PPI All Commodities (FRED: PPIACO)."""
        return self._get_fred('PPIACO', start, end)

    # -- Growth & Production (FRED) --

    def real_gdp(self, start=None, end=None):
        """Real Gross Domestic Product (FRED: GDPC1)."""
        return self._get_fred('GDPC1', start, end)

    def capacity_utilization(self, start=None, end=None):
        """Capacity Utilization: Total Industry % (FRED: TCU)."""
        return self._get_fred('TCU', start, end)

    def durable_goods_orders(self, start=None, end=None):
        """Manufacturers' Durable Goods New Orders (FRED: DGORDER)."""
        return self._get_fred('DGORDER', start, end)

    # -- Financial Conditions (FRED) --

    def financial_stress_index(self, start=None, end=None):
        """St. Louis Fed Financial Stress Index (FRED: STLFSI4)."""
        return self._get_fred('STLFSI4', start, end)

    def nfci(self, start=None, end=None):
        """Chicago Fed National Financial Conditions Index (FRED: NFCI)."""
        return self._get_fred('NFCI', start, end)

    # -- Leading Indicators (FRED) --

    def leading_index(self, start=None, end=None):
        """Leading Index for the US (FRED: USSLIND). Stale since 2020."""
        return self._get_fred('USSLIND', start, end)

    def chicago_national_activity(self, start=None, end=None):
        """Chicago Fed National Activity Index (FRED: CFNAI)."""
        return self._get_fred('CFNAI', start, end)

    def empire_state(self, start=None, end=None):
        """Empire State Manufacturing Survey — General Business Conditions (FRED: GACDISA066MSFRBNY)."""
        return self._get_fred('GACDISA066MSFRBNY', start, end)

    # -- Global Indicators (FRED) --

    def global_epu(self, start=None, end=None):
        """Global Economic Policy Uncertainty Index (FRED: GEPUPPP)."""
        return self._get_fred('GEPUPPP', start, end)

    def dxy(self, start=None, end=None):
        """Trade Weighted US Dollar Index: Broad (FRED: DTWEXBGS)."""
        return self._get_fred('DTWEXBGS', start, end)

    # -- Global Sovereign Bond Yields (FRED) --

    def sovereign_yield_korea(self, start=None, end=None):
        """Korea 10Y Government Bond Yield (FRED: IRLTLT01KRM156N)."""
        return self._get_fred('IRLTLT01KRM156N', start, end)

    def sovereign_yield_australia(self, start=None, end=None):
        """Australia 10Y Government Bond Yield (FRED: IRLTLT01AUM156N)."""
        return self._get_fred('IRLTLT01AUM156N', start, end)

    def sovereign_yield_canada(self, start=None, end=None):
        """Canada 10Y Government Bond Yield (FRED: IRLTLT01CAM156N)."""
        return self._get_fred('IRLTLT01CAM156N', start, end)

    def sovereign_yield_germany(self, start=None, end=None):
        """Germany 10Y Government Bond Yield (FRED: IRLTLT01DEM156N)."""
        return self._get_fred('IRLTLT01DEM156N', start, end)

    def sovereign_yield_france(self, start=None, end=None):
        """France 10Y Government Bond Yield (FRED: IRLTLT01FRM156N)."""
        return self._get_fred('IRLTLT01FRM156N', start, end)

    def sovereign_yield_italy(self, start=None, end=None):
        """Italy 10Y Government Bond Yield (FRED: IRLTLT01ITM156N)."""
        return self._get_fred('IRLTLT01ITM156N', start, end)

    def sovereign_yield_uk(self, start=None, end=None):
        """UK 10Y Government Bond Yield (FRED: IRLTLT01GBM156N)."""
        return self._get_fred('IRLTLT01GBM156N', start, end)

    def sovereign_yield_spain(self, start=None, end=None):
        """Spain 10Y Government Bond Yield (FRED: IRLTLT01ESM156N)."""
        return self._get_fred('IRLTLT01ESM156N', start, end)

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
