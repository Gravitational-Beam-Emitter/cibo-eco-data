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
            df = pd.DataFrame(data['response']['data'])
            # Normalize: EIA v2 uses 'period' for date
            if 'period' in df.columns:
                df = df.rename(columns={'period': 'date'})
            df = df[['date', 'value']].copy()
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            return df.dropna(subset=['value']).sort_values('date').reset_index(drop=True)
        return pd.DataFrame(data.get('series', []))

    def crude_price(self):
        """WTI Crude Oil spot price (weekly, USD/barrel)."""
        return self._get('petroleum/pri/spt/data',
                         frequency='weekly', offset=0, length=5000,
                         **{'data[0]': 'value',
                            'facets[product][]': 'EPCWTI'})

    def natural_gas_price(self):
        """Henry Hub Natural Gas spot price (monthly, USD/MMBtu)."""
        return self._get('natural-gas/pri/fut/data',
                         frequency='monthly', offset=0, length=5000,
                         **{'data[0]': 'value',
                            'facets[series][]': 'RNGWHHD',
                            'sort[0][column]': 'period',
                            'sort[0][direction]': 'asc'})
