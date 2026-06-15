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
        """WTI Crude Oil spot price (weekly, USD/barrel)."""
        return self._get('petroleum/pri/spt/data',
                         frequency='weekly', offset=0, length=5000,
                         **{'data[0]': 'value',
                            'facets[product][]': 'EPCWTI'})

    def natural_gas_price(self):
        """Henry Hub Natural Gas spot price (monthly)."""
        return self._get('natural-gas/pri/fut/data',
                         frequency='monthly', offset=0, length=5000,
                         **{'data[0]': 'value',
                            'facets[series][]': 'RNGC1',
                            'sort[0][column]': 'period',
                            'sort[0][direction]': 'asc'})
