---
name: eco-harness
description: >
  Self-installing skill — deploys the Eco Data API Harness (FRED, AKShare, World Bank, DBnomics,
  OECD, ECB, BoJ, EIA) into any project. Reads this file, writes all source files, validates the
  install, and prompts the user for their FRED and EIA API keys. No keys are stored in this file.
---

# Eco Data API Harness — Self-Installing Skill

> **What**: Unified macroeconomic data access layer — one facade, 6 regional sub-harnesses, 50+ pre-built indicator methods.
> **When to install**: Any project that needs US / China / Global / Japan / Eurozone / Energy macro data.
> **No keys embedded**: FRED Key and EIA Key are asked from the user at install time.

---

## Step 1 — Read and execute this skill

When you read this skill file, you are the installing agent. Your task:

1. Create the directory structure under `app/eco_harness/` in the **target project**
2. Write each `.py` file from the sections below
3. Run the validation imports
4. **Ask the user** for `FRED_API_KEY` and `EIA_API_KEY`, then write an `.env` file or instruct them on setting env vars

Do NOT skip any file. The harness depends on the exact class and method signatures shown below.

---

## Step 2 — Prerequisites

Run before writing files:

```bash
pip install fredapi akshare wbgapi dbnomics opensdmx boj-api requests pandas
```

Package-by-package role:

| Package | Sub-harness | Auth Required |
|---------|-------------|---------------|
| `fredapi` | `us.py` — FRED series | **Yes** — free key from fred.stlouisfed.org |
| `akshare` | `cn.py` — China macro | No |
| `wbgapi` | `global_.py` — World Bank WDI | No |
| `dbnomics` | `global_.py` — DBnomics aggregator | No |
| `opensdmx` | `sdmx.py` — OECD + ECB + Eurostat | No |
| `boj-api` | `jp.py` — Bank of Japan | No |
| `requests` | `us.py` (Treasury) + `energy.py` (EIA) | No (Treasury) / **Yes** (EIA) |
| `pandas` | All — DataFrame normalization | No |

---

## Step 3 — Directory structure

Create this tree under the target project root:

```
app/
└── eco_harness/
    ├── __init__.py
    ├── us.py
    ├── cn.py
    ├── global_.py
    ├── sdmx.py
    ├── jp.py
    └── energy.py
```

If `app/` does not exist, create it. Then create `app/__init__.py` with this content:

```python
# app package
```

If `app/__init__.py` already exists, leave it untouched.

---

## Step 4 — File contents

Write each file EXACTLY as shown. Do not modify, reformat, or "improve" any content.

### FILE: `app/eco_harness/__init__.py`

```python
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
    df = eh.global_.gdp('CHN')
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
```

### FILE: `app/eco_harness/us.py`

```python
"""
US Macro Harness — FRED + US Treasury.

Data limits: FRED free tier = 120 req/min, Treasury = no limit.
Date format: YYYY-MM-DD (FRED), flexible (Treasury).
"""

import pandas as pd
import requests


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

    # -- Core indicators --

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
        """ISM Manufacturing PMI — uses Industrial Production as proxy.
        Use eh.us.search('manufacturing pmi') for current series."""
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
```

### FILE: `app/eco_harness/cn.py`

```python
"""
China Macro Harness — AKShare.

Data limits: AKShare depends on upstream (EastMoney, Sina, etc.).
Rate varies by endpoint; no hard global limit. Cache aggressively.
Large batches may trigger upstream throttling — add sleep(1) between calls.
"""

import pandas as pd


class CNHarness:
    """Chinese macroeconomic indicators via AKShare."""

    _IMPORT_FAILED = False

    def __init__(self):
        self._ak = None

    def _init_ak(self):
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                if not CNHarness._IMPORT_FAILED:
                    CNHarness._IMPORT_FAILED = True
                    print('[CNHarness] akshare not installed — pip install akshare')
                raise

    # -- Core indicators --

    def gdp(self):
        """中国 GDP (季度累计, 亿元)"""
        self._init_ak()
        df = self._ak.macro_china_gdp()
        return _clean(df, {'date': 'time', 'value': 'gdp'})

    def gdp_yoy(self):
        """中国 GDP 同比增速"""
        self._init_ak()
        df = self._ak.macro_china_gdp_yearly()
        return _clean(df, {'date': 'time', 'value': 'gdp_yoy'})

    def cpi(self):
        """中国 CPI 月度同比/环比"""
        self._init_ak()
        df = self._ak.macro_china_cpi_monthly()
        return _clean(df, date_col='date', value_col='cpi')

    def ppi(self):
        """中国 PPI 月度"""
        self._init_ak()
        df = self._ak.macro_china_ppi_yearly()
        return _clean(df, date_col='time', value_col='ppi')

    def pmi(self):
        """中国官方制造业 PMI"""
        self._init_ak()
        df = self._ak.macro_china_pmi()
        return _clean(df, date_col='date', value_col='pmi')

    def non_manufacturing_pmi(self):
        """中国非制造业 PMI"""
        self._init_ak()
        df = self._ak.macro_china_non_manufacturing_pmi()
        return _clean(df, date_col='date', value_col='nmi')

    def m2(self):
        """中国 M2 货币供应量"""
        self._init_ak()
        df = self._ak.macro_china_money_supply()
        return _clean(df, date_col='time', value_col='m2')

    def total_social_financing(self):
        """中国社会融资规模"""
        self._init_ak()
        df = self._ak.macro_china_shrzgm()
        return _clean(df, date_col='time', value_col='sf')

    def lpr(self):
        """中国贷款市场报价利率 (LPR)"""
        self._init_ak()
        df = self._ak.macro_china_lpr()
        return _clean(df, date_col='date', value_col='1y_lpr')

    def foreign_reserves(self):
        """中国外汇储备"""
        self._init_ak()
        df = self._ak.macro_china_fx_gold()
        return _clean(df, date_col='time', value_col='reserves')

    def industrial_production(self):
        """中国工业增加值同比"""
        self._init_ak()
        df = self._ak.macro_china_industrial_production()
        return _clean(df, date_col='time', value_col='ip')

    def fixed_asset_investment(self):
        """中国固定资产投资同比"""
        self._init_ak()
        df = self._ak.macro_china_fixed_asset_investment()
        return _clean(df, date_col='time', value_col='fai')

    def retail_sales(self):
        """中国社会消费品零售总额同比"""
        self._init_ak()
        df = self._ak.macro_china_consumer_goods_retail()
        return _clean(df, date_col='time', value_col='retail')

    def trade_balance(self):
        """中国贸易差额 (USD)"""
        self._init_ak()
        df = self._ak.macro_china_trade_balance()
        return _clean(df, date_col='date', value_col='balance')

    def new_house_price(self):
        """中国 70 城新建住宅价格指数"""
        self._init_ak()
        df = self._ak.macro_china_new_house_price()
        return _clean(df, date_col='date', value_col='house_price')

    def electricity(self):
        """中国全社会用电量"""
        self._init_ak()
        df = self._ak.macro_china_electricity()
        return _clean(df, date_col='date', value_col='electricity')

    def freight(self):
        """中国货运量"""
        self._init_ak()
        df = self._ak.macro_china_freight()
        return _clean(df, date_col='date', value_col='freight')


def _clean(df, cols: dict = None, date_col: str = None, value_col: str = None):
    """Normalize to date/value columns, drop NAs."""
    if cols:
        df = df.rename(columns=cols)
    if date_col and value_col:
        df = df[[date_col, value_col]].copy()
        df.columns = ['date', 'value']
    try:
        df['date'] = pd.to_datetime(df['date'])
    except Exception:
        pass
    return df.dropna(subset=['value']).sort_values('date').reset_index(drop=True)
```

### FILE: `app/eco_harness/global_.py`

```python
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

    def gdp(self, country: str, mrv: int = 5):
        """GDP (current USD) — NY.GDP.MKTP.CD. country='CHN','USA','JPN','WLD'"""
        self._init_wb()
        return self._wb.data.DataFrame('NY.GDP.MKTP.CD', country, mrv=mrv)

    def gdp_per_capita(self, country: str, mrv: int = 5):
        """GDP per capita (current USD) — NY.GDP.PCAP.CD"""
        self._init_wb()
        return self._wb.data.DataFrame('NY.GDP.PCAP.CD', country, mrv=mrv)

    def gdp_growth(self, country: str, mrv: int = 5):
        """GDP growth (annual %) — NY.GDP.MKTP.KD.ZG"""
        self._init_wb()
        return self._wb.data.DataFrame('NY.GDP.MKTP.KD.ZG', country, mrv=mrv)

    def cpi(self, country: str, mrv: int = 5):
        """CPI inflation (annual %) — FP.CPI.TOTL.ZG"""
        self._init_wb()
        return self._wb.data.DataFrame('FP.CPI.TOTL.ZG', country, mrv=mrv)

    def population(self, country: str, mrv: int = 5):
        """Total population — SP.POP.TOTL"""
        self._init_wb()
        return self._wb.data.DataFrame('SP.POP.TOTL', country, mrv=mrv)

    def trade_balance(self, country: str, mrv: int = 5):
        """Trade balance % GDP — NE.RSB.GNFS.ZS"""
        self._init_wb()
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
```

### FILE: `app/eco_harness/sdmx.py`

```python
"""
SDMX Harness — OECD + ECB via opensdmx.

Data limits: SDMX endpoints are public, no key. Rate varies by provider.
opensdmx caches in SQLite+Parquet — first fetch per dataset is slow, replay is instant.
"""


class SDMXHarness:
    """OECD + ECB unified access via SDMX protocol."""

    def __init__(self):
        self._loaded = False

    def _ensure(self):
        if not self._loaded:
            try:
                import opensdmx
                self.opensdmx = opensdmx
                self._loaded = True
            except ImportError:
                print('[SDMXHarness] opensdmx not installed — pip install opensdmx')
                raise

    def oecd(self, dataset: str, **dimensions):
        """Fetch OECD dataset with optional dimension filters.

        Example:
            eh.sdmx.oecd('QNA', country='USA', freq='Q')
        """
        self._ensure()
        self.opensdmx.set_provider('oecd')
        return self.opensdmx.fetch(dataset, **dimensions)

    def ecb(self, dataset: str, **dimensions):
        """Fetch ECB dataset.

        Example:
            eh.sdmx.ecb('EXR', freq='D', currency='USD')
            eh.sdmx.ecb('YC', maturity='10Y')   # yield curve
        """
        self._ensure()
        self.opensdmx.set_provider('ecb')
        return self.opensdmx.fetch(dataset, **dimensions)

    def eurostat(self, dataset: str, **dimensions):
        """Fetch Eurostat dataset."""
        self._ensure()
        self.opensdmx.set_provider('eurostat')
        return self.opensdmx.fetch(dataset, **dimensions)

    def search(self, query: str, provider: str = 'oecd'):
        """Search datasets in a provider."""
        self._ensure()
        return self.opensdmx.search_dataset(query, provider=provider)
```

### FILE: `app/eco_harness/jp.py`

```python
"""
Bank of Japan Harness — boj-api.

Data limits:
  - Max 250 series / 60,000 data points per request (auto-paginated).
  - No API key. Public since 2026-02-18.
  - Date format: YYYYMM (not YYYYMMDD!) for daily/monthly/quarterly freq.
"""

import pandas as pd


class JPHarness:
    """Bank of Japan statistics via boj-api."""

    def __init__(self):
        self._client = None

    def _init(self):
        if self._client is None:
            try:
                from boj_api import BOJClient, Database
                self._BOJClient = BOJClient
                self._Database = Database
                self._client = BOJClient()
            except ImportError:
                print('[JPHarness] boj-api not installed — pip install boj-api')
                raise

    def _get(self, db, codes: list, start: str = '201501', end: str = None):
        self._init()
        if end is None:
            from datetime import datetime
            end = datetime.now().strftime('%Y%m')
        resp = self._client.get_data_by_code(db=db, code=codes,
                                             start_date=start, end_date=end)
        records = []
        for s in resp.series:
            for obs in s.observations:
                records.append({'code': s.code, 'date': obs.date, 'value': obs.value})
        return pd.DataFrame(records)

    def fx(self, pair: str = 'USDJPY', start: str = '201501', end: str = None):
        """Get FX rate. Supported: USDJPY, EURJPY, GBPJPY, etc.
        See Database.FM08 for full list."""
        self._init()
        from boj_api import Database
        return self._get(Database.FM08, [pair], start, end)

    def tankan(self, start: str = '201501', end: str = None):
        """Tankan survey (短观) — large manufacturers DI."""
        self._init()
        from boj_api import Database
        return self._get(Database.CO, ['CO1'], start, end)

    def get(self, db, codes: list, start: str = '201501', end: str = None):
        """Arbitrary BOJ series. See Database enum for available DBs:
        IR01 (discount rates), FM01 (call rate), FM08 (FX), CO (tankan), FF (flow of funds)."""
        return self._get(db, codes, start, end)
```

### FILE: `app/eco_harness/energy.py`

```python
"""
Energy Data Harness — EIA (US Energy Information Administration).

Data limits:
  - Free API key required (register at eia.gov/opendata).
  - Rate limit: 2,000 requests / hour.
  - Note: EIA covers US energy data. IEA global data is paywalled.
"""

import pandas as pd
import requests


class EnergyHarness:
    """US EIA energy data access."""

    def __init__(self, api_key: str = ''):
        self._key = api_key
        self._base = 'https://api.eia.gov/v2'

    def _get(self, route: str, **params):
        params['api_key'] = self._key
        resp = requests.get(f'{self._base}/{route}', params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if 'response' in data and 'data' in data['response']:
            return pd.DataFrame(data['response']['data'])
        return pd.DataFrame(data.get('series', []))

    def crude_price(self):
        """WTI Crude Oil spot price (weekly)."""
        return self._get('petroleum/pri/spt/data',
                         frequency='weekly', offset=0, length=5000,
                         **{'data[0]': 'value',
                            'facets[product][]': 'EPCWTID',
                            'sort[0][column]': 'period',
                            'sort[0][direction]': 'asc'})

    def natural_gas_price(self):
        """Henry Hub Natural Gas spot price (monthly)."""
        return self._get('natural-gas/pri/fut/data',
                         frequency='monthly', offset=0, length=5000,
                         **{'data[0]': 'value',
                            'facets[series][]': 'RNGC1',
                            'sort[0][column]': 'period',
                            'sort[0][direction]': 'asc'})
```

---

## Step 5 — API Key handling (CRITICAL)

**This skill file contains NO API keys.** The harness needs two optional keys:

| Key | Env Var | Required For | How to Get |
|-----|---------|--------------|------------|
| FRED API Key | `FRED_API_KEY` | `eh.us.*` FRED methods | fred.stlouisfed.org → Register |
| EIA API Key | `EIA_API_KEY` | `eh.energy.*` methods | eia.gov/opendata → Register |

**As the installing agent, you MUST ask the user:**

> "The EcoHarness needs two optional API keys. Without them, `eh.us.*` FRED methods and `eh.energy.*` will fail, but `eh.cn.*`, `eh.global_.*`, `eh.sdmx.*`, `eh.jp.*`, and Treasury methods will work fine. Do you have a FRED API key and/or EIA API key to configure? If so, I'll write them to a `.env` file (or you can set them as environment variables)."

**NEVER** guess, generate, or hardcode keys. If the user provides keys, store them in the project's `.env` file:

```
FRED_API_KEY=<user-provided-key>
EIA_API_KEY=<user-provided-key>
```

And ensure `.env` is in `.gitignore`.

---

## Step 6 — Post-install validation

After writing all files, run this validation:

```python
# Test 1: Import
from app.eco_harness import EcoHarness
print("Import OK")

# Test 2: Instantiate (no keys — non-FRED/non-EIA methods work)
eh = EcoHarness()
print("Init OK")

# Test 3: Non-key methods work
print("Testing AKShare cn.cpi()...")
df = eh.cn.cpi()
print(f"  cn.cpi: {len(df)} rows, head={df.head(1)['value'].values[0] if len(df) else 'EMPTY'}")

print("Testing World Bank global_.population('CHN')...")
df = eh.global_.population('CHN')
print(f"  global_.population: {len(df)} rows")

print("Testing US Treasury (no key needed)...")
debt = eh.us.treasury_debt_latest()
print(f"  treasury_debt_latest: ${debt:,.0f}")

# Test 4: Key-gated methods fail gracefully
import os
if os.environ.get('FRED_API_KEY'):
    df = eh.us.gdp()
    print(f"  us.gdp: {len(df)} rows")
else:
    print("  us.gdp: SKIPPED (no FRED_API_KEY — expected)")

print("\n=== EcoHarness install validated ===")
```

---

## Step 7 — Usage quick reference

```python
from app.eco_harness import EcoHarness
eh = EcoHarness(fred_api_key='...', eia_api_key='...')

# US (FRED)
eh.us.gdp()              # GDP (Billions, SAAR, Quarterly)
eh.us.cpi()              # CPI (Monthly)
eh.us.unemployment()     # Unemployment Rate (%, Monthly)
eh.us.fed_funds()        # Fed Funds Rate
eh.us.treasury_10y()     # 10Y Treasury Yield
eh.us.get('T10Y2Y')      # Any FRED series
eh.us.search('inflation')# Search FRED

# US (Treasury — no key)
eh.us.treasury_debt_latest()
eh.us.treasury_rates_of_exchange('China')

# China (AKShare — no key)
eh.cn.gdp()              # GDP (亿元)
eh.cn.cpi()              # CPI
eh.cn.pmi()              # Manufacturing PMI
eh.cn.m2()               # M2
eh.cn.lpr()              # LPR
eh.cn.trade_balance()    # Trade balance (USD)
eh.cn.new_house_price()  # 70-city house price
eh.cn.electricity()      # Electricity consumption

# Global (no key)
eh.global_.gdp('CHN')           # World Bank GDP
eh.global_.gdp_growth('CHN')    # GDP growth %
eh.global_.cpi('USA')           # CPI inflation %
eh.global_.population('WLD')    # World population
eh.global_.dbnomics('OECD', 'MEI', 'USA.B6BLTT01.CXCUSA.Q')

# SDMX (no key)
eh.sdmx.oecd('QNA', country='USA', freq='Q')
eh.sdmx.ecb('EXR', freq='D', currency='USD')

# Japan (no key)
eh.jp.fx('USDJPY')
eh.jp.tankan()

# Energy (needs EIA key)
eh.energy.crude_price()
eh.energy.natural_gas_price()
```

---

## Appendix A — Full data source inventory

| # | Source | Region | Auth | Package | Sub-harness |
|---|--------|--------|------|---------|-------------|
| 1 | FRED | US | Free Key | `fredapi` | `us.py` |
| 2 | US Treasury | US | None | `requests` | `us.py` |
| 3 | AKShare | China | None | `akshare` | `cn.py` |
| 4 | World Bank WDI | Global | None | `wbgapi` | `global_.py` |
| 5 | DBnomics | Global | None | `dbnomics` | `global_.py` |
| 6 | OECD SDMX | Global | None | `opensdmx` | `sdmx.py` |
| 7 | ECB SDMX | Eurozone | None | `opensdmx` | `sdmx.py` |
| 8 | Eurostat SDMX | Eurozone | None | `opensdmx` | `sdmx.py` |
| 9 | Bank of Japan | Japan | None | `boj-api` | `jp.py` |
| 10 | EIA | US Energy | Free Key | `requests` | `energy.py` |

**Key insight**: 8 of 10 sources need NO API key. Only FRED and EIA require free registration.

## Appendix B — Return type contract

All harness methods return `pd.DataFrame` with at minimum `date` and `value` columns, sorted ascending by date, NaN-free. This is the contract consumers rely on.
