"""
Indicator registry — defines which economic indicators to fetch and store.

Each entry maps to a method on one of the EcoHarness sub-harnesses.
Format: (source, name, method, params_dict, description, frequency)
"""

from __future__ import annotations

from typing import Optional

INDICATORS = [
    # ── US (FRED) ────────────────────────────────────────────
    {"source": "us", "name": "GDP", "method": "gdp", "params": {},
     "description": "US GDP (Billions, SAAR, Quarterly)", "frequency": "quarterly"},
    {"source": "us", "name": "CPI", "method": "cpi", "params": {},
     "description": "US CPI (1982-84=100, Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "Core CPI", "method": "core_cpi", "params": {},
     "description": "US Core CPI (ex Food & Energy, Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "Unemployment Rate", "method": "unemployment", "params": {},
     "description": "US Unemployment Rate (%, Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "Nonfarm Payrolls", "method": "nonfarm", "params": {},
     "description": "US Nonfarm Payrolls (thousands, Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "Fed Funds Rate", "method": "fed_funds", "params": {},
     "description": "Federal Funds Effective Rate (%, Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "10Y Treasury Yield", "method": "treasury_10y", "params": {},
     "description": "10-Year Treasury Constant Maturity Rate (%, Daily)", "frequency": "daily"},
    {"source": "us", "name": "2Y Treasury Yield", "method": "treasury_2y", "params": {},
     "description": "2-Year Treasury Constant Maturity Rate (%, Daily)", "frequency": "daily"},
    {"source": "us", "name": "Industrial Production", "method": "industrial", "params": {},
     "description": "US Industrial Production Index (Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "M2 Money Supply", "method": "m2", "params": {},
     "description": "US M2 Money Supply (Billions, Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "Retail Sales", "method": "retail_sales", "params": {},
     "description": "US Retail Sales (Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "Trade Balance", "method": "trade_balance", "params": {},
     "description": "US Trade Balance (Monthly)", "frequency": "monthly"},
    {"source": "us", "name": "Federal Debt % GDP", "method": "debt_gdp", "params": {},
     "description": "US Federal Debt as % of GDP (Quarterly)", "frequency": "quarterly"},

    # ── China (AKShare) ─────────────────────────────────────
    {"source": "cn", "name": "GDP", "method": "gdp", "params": {},
     "description": "中国 GDP (季度累计, 亿元)", "frequency": "quarterly"},
    {"source": "cn", "name": "GDP YoY", "method": "gdp_yoy", "params": {},
     "description": "中国 GDP 同比增速 (%)", "frequency": "quarterly"},
    {"source": "cn", "name": "CPI", "method": "cpi", "params": {},
     "description": "中国 CPI 月度同比/环比", "frequency": "monthly"},
    {"source": "cn", "name": "PPI", "method": "ppi", "params": {},
     "description": "中国 PPI 月度同比", "frequency": "monthly"},
    {"source": "cn", "name": "Manufacturing PMI", "method": "pmi", "params": {},
     "description": "中国官方制造业 PMI", "frequency": "monthly"},
    {"source": "cn", "name": "Non-Manufacturing PMI", "method": "non_manufacturing_pmi", "params": {},
     "description": "中国非制造业 PMI", "frequency": "monthly"},
    {"source": "cn", "name": "M2 Money Supply", "method": "m2", "params": {},
     "description": "中国 M2 货币供应量 (亿元)", "frequency": "monthly"},
    {"source": "cn", "name": "Total Social Financing", "method": "total_social_financing", "params": {},
     "description": "中国社会融资规模 (亿元)", "frequency": "monthly"},
    {"source": "cn", "name": "LPR", "method": "lpr", "params": {},
     "description": "中国贷款市场报价利率 LPR (%)", "frequency": "monthly"},
    {"source": "cn", "name": "Foreign Reserves", "method": "foreign_reserves", "params": {},
     "description": "中国外汇储备 (亿美元)", "frequency": "monthly"},
    {"source": "cn", "name": "Industrial Production", "method": "industrial_production", "params": {},
     "description": "中国工业增加值同比 (%)", "frequency": "monthly"},
    {"source": "cn", "name": "Fixed Asset Investment", "method": "fixed_asset_investment", "params": {},
     "description": "中国固定资产投资同比 (%)", "frequency": "monthly"},
    {"source": "cn", "name": "Retail Sales", "method": "retail_sales", "params": {},
     "description": "中国社会消费品零售总额同比 (%)", "frequency": "monthly"},
    {"source": "cn", "name": "Trade Balance", "method": "trade_balance", "params": {},
     "description": "中国贸易差额 (亿美元)", "frequency": "monthly"},
    {"source": "cn", "name": "New House Price", "method": "new_house_price", "params": {},
     "description": "中国 70 城新建住宅价格指数", "frequency": "monthly"},
    {"source": "cn", "name": "Electricity", "method": "electricity", "params": {},
     "description": "中国全社会用电量 (亿千瓦时)", "frequency": "monthly"},
    {"source": "cn", "name": "Freight", "method": "freight", "params": {},
     "description": "中国货运量", "frequency": "monthly"},
    {"source": "cn", "name": "North Bound Flow", "method": "north_bound_flow", "params": {},
     "description": "北向资金每日净流入 (亿元)", "frequency": "daily"},
    {"source": "cn", "name": "Margin Balance", "method": "margin_balance", "params": {},
     "description": "融资融券余额 (亿元)", "frequency": "daily"},
    {"source": "cn", "name": "Market Volume", "method": "market_volume", "params": {},
     "description": "上证指数成交量 (亿股)", "frequency": "daily"},
    {"source": "cn", "name": "New Investors", "method": "new_investors", "params": {},
     "description": "A股新增投资者数量 (万户)", "frequency": "monthly"},
    {"source": "cn", "name": "10Y Bond Yield", "method": "bond_yield_10y", "params": {},
     "description": "中国10年期国债收益率 (%)", "frequency": "daily"},
    {"source": "cn", "name": "CNY/USD", "method": "cny_usd", "params": {},
     "description": "人民币汇率中间价 (美元兑人民币)", "frequency": "daily"},
    {"source": "cn", "name": "Caixin PMI", "method": "caixin_pmi", "params": {},
     "description": "财新制造业 PMI", "frequency": "monthly"},
    {"source": "cn", "name": "Enterprise Boom", "method": "enterprise_boom", "params": {},
     "description": "企业景气指数", "frequency": "quarterly"},
    {"source": "cn", "name": "Shibor 3M", "method": "shibor_3m", "params": {},
     "description": "Shibor 3个月利率 (%)", "frequency": "daily"},
    {"source": "cn", "name": "Reserve Ratio", "method": "reserve_ratio", "params": {},
     "description": "存款准备金率 (大型金融机构, %)", "frequency": "monthly"},

    # ── Global (World Bank) ─────────────────────────────────
    {"source": "global_", "name": "GDP China", "method": "gdp", "params": {"country": "CHN"},
     "description": "China GDP current USD (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "GDP USA", "method": "gdp", "params": {"country": "USA"},
     "description": "US GDP current USD (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "GDP Japan", "method": "gdp", "params": {"country": "JPN"},
     "description": "Japan GDP current USD (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "GDP World", "method": "gdp", "params": {"country": "WLD"},
     "description": "World GDP current USD (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "GDP Growth China", "method": "gdp_growth", "params": {"country": "CHN"},
     "description": "China GDP growth annual % (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "GDP Growth USA", "method": "gdp_growth", "params": {"country": "USA"},
     "description": "US GDP growth annual % (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "CPI China", "method": "cpi", "params": {"country": "CHN"},
     "description": "China CPI inflation annual % (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "CPI USA", "method": "cpi", "params": {"country": "USA"},
     "description": "US CPI inflation annual % (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "Population China", "method": "population", "params": {"country": "CHN"},
     "description": "China total population (World Bank)", "frequency": "yearly"},
    {"source": "global_", "name": "Population World", "method": "population", "params": {"country": "WLD"},
     "description": "World total population (World Bank)", "frequency": "yearly"},

    # ── Japan (BoJ) ─────────────────────────────────────────
    {"source": "jp", "name": "USDJPY", "method": "fx", "params": {"pair": "USDJPY"},
     "description": "USD/JPY exchange rate (Bank of Japan)", "frequency": "monthly"},
    {"source": "jp", "name": "Tankan Survey", "method": "tankan", "params": {},
     "description": "Tankan 短观调查 — 大型制造业 DI (Bank of Japan)", "frequency": "quarterly"},

    # ── Energy (EIA) ───────────────────────────────────────
    {"source": "energy", "name": "WTI Crude Oil Price", "method": "crude_price", "params": {},
     "description": "WTI Crude Oil spot price (weekly, USD/barrel)", "frequency": "weekly"},
    {"source": "energy", "name": "Henry Hub Natural Gas", "method": "natural_gas_price", "params": {},
     "description": "Henry Hub Natural Gas spot price (monthly, USD/MMBtu)", "frequency": "monthly"},
]

# Indicators that require API keys — skipped if key not configured
_REQUIRES_FRED_KEY = {"us.gdp", "us.cpi", "us.core_cpi", "us.unemployment", "us.nonfarm",
                       "us.fed_funds", "us.treasury_10y", "us.treasury_2y", "us.industrial",
                       "us.m2", "us.retail_sales", "us.trade_balance", "us.debt_gdp"}
_REQUIRES_EIA_KEY = {"energy.crude_price", "energy.natural_gas_price"}


def requires_api_key(source: str, method: str) -> Optional[str]:
    """Return 'FRED' / 'EIA' if the indicator needs that key, else None."""
    key = f"{source}.{method}"
    if key in _REQUIRES_FRED_KEY:
        return "FRED"
    if key in _REQUIRES_EIA_KEY:
        return "EIA"
    return None
