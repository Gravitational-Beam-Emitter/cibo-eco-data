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
