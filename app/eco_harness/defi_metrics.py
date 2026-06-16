"""
DeFi & Prediction Market Metrics — on-chain financial activity indicators.

Tracks:
  - Polymarket prediction market volume (crowd wisdom aggregation)
  - DeFi DEX & derivatives volumes (on-chain trading activity)
  - RWA (Real World Assets) TVL (tokenized traditional assets)
  - CoinGecko exchange volumes (CEX + DEX benchmarks)

These are forward-looking indicators:
  - Prediction market volume = uncertainty pricing & risk appetite
  - On-chain trading volume = crypto-native financial activity
  - RWA TVL = TradFi assets migrating on-chain

Update: daily snapshots recommended.
"""

from __future__ import annotations

import pandas as pd
import requests
import time
from datetime import date


class DeFiMetricsHarness:
    """On-chain and prediction market metrics."""

    def __init__(self):
        self._sess = requests.Session()

    # ── Polymarket (Prediction Markets) ─────────────────

    def polymarket_volume(self):
        """Aggregate total volume across all Polymarket markets.
        Prediction market volume = crowd wisdom activity indicator."""
        total_vol, total_liq, n_markets = 0.0, 0.0, 0
        for offset in range(0, 1000, 100):
            try:
                resp = self._sess.get(
                    'https://gamma-api.polymarket.com/markets',
                    params={'limit': 100, 'offset': offset},
                    timeout=20
                )
                if resp.ok:
                    markets = resp.json()
                    if not markets:
                        break
                    n_markets += len(markets)
                    for m in markets:
                        total_vol += float(m.get('volume', 0) or 0)
                        total_liq += float(m.get('liquidity', 0) or 0)
                    if len(markets) < 100:
                        break
                time.sleep(0.2)
            except Exception:
                break

        return pd.DataFrame([{
            "date": str(date.today()),
            "value": total_vol,
        }])

    def polymarket_market_count(self):
        """Number of active Polymarket prediction markets."""
        count = 0
        for offset in range(0, 1000, 100):
            try:
                resp = self._sess.get(
                    'https://gamma-api.polymarket.com/markets',
                    params={'limit': 100, 'offset': offset},
                    timeout=20
                )
                if resp.ok:
                    markets = resp.json()
                    if not markets:
                        break
                    count += len(markets)
                    if len(markets) < 100:
                        break
                time.sleep(0.2)
            except Exception:
                break
        return pd.DataFrame([{
            "date": str(date.today()),
            "value": count,
        }])

    def polymarket_top_market_volume(self):
        """Volume of the single largest Polymarket market — risk focus indicator."""
        try:
            resp = self._sess.get(
                'https://gamma-api.polymarket.com/markets',
                params={'limit': 100, 'offset': 0, 'order': 'volume', 'ascending': 'false'},
                timeout=20
            )
            if resp.ok:
                markets = resp.json()
                max_vol = max(float(m.get('volume', 0) or 0) for m in markets)
                return pd.DataFrame([{"date": str(date.today()), "value": max_vol}])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    # ── DeFi DEX & Derivatives ──────────────────────────

    def defi_dex_total_tvl(self):
        """Total Value Locked across all DeFi DEX protocols."""
        try:
            resp = self._sess.get('https://api.llama.fi/protocols', timeout=30)
            if resp.ok:
                protos = resp.json()
                dex_protos = [p for p in protos if p.get('category') == 'Dexs']
                total_tvl = sum(p.get('tvl', 0) or 0 for p in dex_protos)
                return pd.DataFrame([{"date": str(date.today()), "value": total_tvl}])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    def defi_derivatives_tvl(self):
        """Total Value Locked in DeFi derivatives (perpetuals, options)."""
        try:
            resp = self._sess.get('https://api.llama.fi/protocols', timeout=30)
            if resp.ok:
                protos = resp.json()
                deriv_protos = [p for p in protos if p.get('category') == 'Derivatives']
                total_tvl = sum(p.get('tvl', 0) or 0 for p in deriv_protos)
                return pd.DataFrame([{"date": str(date.today()), "value": total_tvl}])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    def defi_dex_24h_volume(self):
        """Total 24h trading volume across all DEX protocols."""
        try:
            resp = self._sess.get(
                'https://api.llama.fi/overview/dexs?excludeTotalDataChart=true'
                '&excludeTotalDataChartBreakdown=true', timeout=20
            )
            if resp.ok:
                data = resp.json()
                total_vol = sum(
                    p.get('total24h', 0) or 0
                    for p in data.get('protocols', [])
                )
                return pd.DataFrame([{"date": str(date.today()), "value": total_vol}])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    def rwa_total_tvl(self):
        """Total Value Locked in Real World Asset protocols — tokenized TradFi."""
        try:
            resp = self._sess.get('https://api.llama.fi/protocols', timeout=30)
            if resp.ok:
                protos = resp.json()
                rwa_protos = [
                    p for p in protos
                    if 'RWA' in (p.get('category', '') or '')
                ]
                total_tvl = sum(p.get('tvl', 0) or 0 for p in rwa_protos)
                return pd.DataFrame([{"date": str(date.today()), "value": total_tvl}])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    def defi_total_protocols(self):
        """Total number of protocols tracked by DeFi Llama."""
        try:
            resp = self._sess.get('https://api.llama.fi/protocols', timeout=30)
            if resp.ok:
                protos = resp.json()
                return pd.DataFrame([{"date": str(date.today()), "value": len(protos)}])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    # ── CoinGecko Exchange Volumes ──────────────────────

    def cex_total_volume_btc(self):
        """Total 24h volume across top centralized exchanges (BTC-denominated)."""
        try:
            resp = self._sess.get(
                'https://api.coingecko.com/api/v3/exchanges?per_page=20',
                timeout=20
            )
            if resp.ok:
                exchanges = resp.json()
                total_btc = sum(
                    float(e.get('trade_volume_24h_btc', 0) or 0)
                    for e in exchanges
                )
                return pd.DataFrame([{"date": str(date.today()), "value": total_btc}])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    def cex_binance_volume_btc(self):
        """Binance 24h volume (BTC) — largest exchange, benchmark for crypto activity."""
        try:
            resp = self._sess.get(
                'https://api.coingecko.com/api/v3/exchanges/binance',
                timeout=20
            )
            if resp.ok:
                data = resp.json()
                vol = data.get('trade_volume_24h_btc', 0) or 0
                return pd.DataFrame([{"date": str(date.today()), "value": float(vol)}])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])
