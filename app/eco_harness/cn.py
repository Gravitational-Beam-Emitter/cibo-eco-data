"""
China Macro Harness — AKShare (1.18.x compatible).

Normalizes all output to date/value DataFrame format.
Data limits: AKShare depends on upstream (EastMoney, Sina, etc.).
Rate varies by endpoint; no hard global limit. Cache aggressively.
"""

from __future__ import annotations

import pandas as pd

_DATE_FORMATS = ["%Y年%m月%d日", "%Y年%m月份", "%Y年%m月", "%Y年第%d季度", "%Y年", "%Y. %m", "%Y.%m"]


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
                    print("[CNHarness] akshare not installed — pip install akshare")
                raise

    # -- Core indicators --

    def gdp(self):
        """中国 GDP (单季度, 亿元) — filters out cumulative rows."""
        self._init_ak()
        df = self._ak.macro_china_gdp()
        # Keep only single-quarter rows (not "1-4季度" cumulative)
        df = df[~df["季度"].str.contains("-")]
        # Parse "2026年第1季度" → date
        df["date"] = df["季度"].apply(_parse_quarter)
        df["value"] = pd.to_numeric(df["国内生产总值-绝对值"], errors="coerce")
        df = df[["date", "value"]].dropna().sort_values("date")
        return df.reset_index(drop=True)

    def gdp_yoy(self):
        """中国 GDP 同比增速 (%)"""
        self._init_ak()
        df = self._ak.macro_china_gdp_yearly()
        return _from_financial_calendar(df)

    def cpi(self):
        """中国 CPI 月度同比/环比"""
        self._init_ak()
        df = self._ak.macro_china_cpi_monthly()
        return _from_financial_calendar(df)

    def ppi(self):
        """中国 PPI 月度同比"""
        self._init_ak()
        df = self._ak.macro_china_ppi_yearly()
        return _from_financial_calendar(df)

    def pmi(self):
        """中国官方制造业 PMI"""
        self._init_ak()
        df = self._ak.macro_china_pmi()
        return _extract(df, date_col="月份", value_col="制造业-指数")

    def non_manufacturing_pmi(self):
        """中国非制造业 PMI"""
        self._init_ak()
        df = self._ak.macro_china_non_man_pmi()
        return _from_financial_calendar(df)

    def m2(self):
        """中国 M2 货币供应量 (亿元)"""
        self._init_ak()
        df = self._ak.macro_china_money_supply()
        return _extract(df, date_col="月份", value_col="货币和准货币(M2)-数量(亿元)")

    def total_social_financing(self):
        """中国社会融资规模 (亿元)"""
        self._init_ak()
        try:
            df = self._ak.macro_china_shrzgm()
            return _extract(df, date_col="月份", value_col="社会融资规模")
        except Exception:
            return _empty()

    def lpr(self):
        """中国贷款市场报价利率 LPR (%)"""
        self._init_ak()
        df = self._ak.macro_china_lpr()
        df = df[["TRADE_DATE", "LPR1Y"]].copy()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)

    def foreign_reserves(self):
        """中国外汇储备 (亿美元)"""
        self._init_ak()
        df = self._ak.macro_china_fx_gold()
        return _extract(df, date_col="月份", value_col="国家外汇储备-数值")

    def industrial_production(self):
        """中国工业增加值同比 (%)"""
        self._init_ak()
        df = self._ak.macro_china_industrial_production_yoy()
        return _from_financial_calendar(df)

    def fixed_asset_investment(self):
        """中国固定资产投资当月 (亿元)"""
        self._init_ak()
        df = self._ak.macro_china_gdzctz()
        return _extract(df, date_col="月份", value_col="当月")

    def retail_sales(self):
        """中国社会消费品零售总额当月 (亿元)"""
        self._init_ak()
        df = self._ak.macro_china_consumer_goods_retail()
        return _extract(df, date_col="月份", value_col="当月")

    def trade_balance(self):
        """中国贸易差额 (亿美元)"""
        self._init_ak()
        df = self._ak.macro_china_trade_balance()
        return _from_financial_calendar(df)

    def new_house_price(self):
        """中国 70 城新建住宅价格指数 (全国均值)"""
        self._init_ak()
        df = self._ak.macro_china_new_house_price()
        price_col = "新建商品住宅价格指数-同比"
        agg = df.groupby("日期")[price_col].mean().reset_index()
        agg.columns = ["date", "value"]
        agg["date"] = pd.to_datetime(agg["date"])
        return agg.dropna().sort_values("date").reset_index(drop=True)

    def electricity(self):
        """中国全社会用电量 (万千瓦时)"""
        self._init_ak()
        df = self._ak.macro_china_society_electricity()
        return _extract(df, date_col="统计时间", value_col="全社会用电量")

    def freight(self):
        """波罗的海干散货指数 BDI"""
        self._init_ak()
        df = self._ak.macro_china_freight_index()
        return _extract(df, date_col="截止日期", value_col="波罗的海综合运价指数BDI")

    # -- Market sentiment indicators --

    def north_bound_flow(self):
        """北向资金每日净流入 (亿元) — 沪股通+深股通合计"""
        self._init_ak()
        try:
            sh = self._ak.stock_hsgt_hist_em(symbol="沪股通")
            sz = self._ak.stock_hsgt_hist_em(symbol="深股通")
        except Exception:
            return _empty()
        sh = sh[["日期", "当日成交净买额"]].copy()
        sh.columns = ["date", "sh"]
        sz = sz[["日期", "当日成交净买额"]].copy()
        sz.columns = ["date", "sz"]
        sh["date"] = pd.to_datetime(sh["date"])
        sz["date"] = pd.to_datetime(sz["date"])
        merged = pd.merge(sh, sz, on="date", how="outer")
        merged["sh"] = pd.to_numeric(merged["sh"], errors="coerce")
        merged["sz"] = pd.to_numeric(merged["sz"], errors="coerce")
        merged["value"] = merged["sh"].fillna(0) + merged["sz"].fillna(0)
        merged = merged[["date", "value"]].dropna(subset=["value"]).sort_values("date")
        return merged.reset_index(drop=True)

    def margin_balance(self):
        """融资融券余额 (亿元) — 上交所+深交所合计"""
        self._init_ak()
        try:
            sh = self._ak.macro_china_market_margin_sh()
            sz = self._ak.macro_china_market_margin_sz()
        except Exception:
            return _empty()
        sh = sh[["日期", "融资融券余额"]].copy()
        sh.columns = ["date", "sh"]
        sz = sz[["日期", "融资融券余额"]].copy()
        sz.columns = ["date", "sz"]
        sh["date"] = pd.to_datetime(sh["date"])
        sz["date"] = pd.to_datetime(sz["date"])
        merged = pd.merge(sh, sz, on="date", how="outer")
        merged["sh"] = pd.to_numeric(merged["sh"], errors="coerce")
        merged["sz"] = pd.to_numeric(merged["sz"], errors="coerce")
        merged["value"] = (merged["sh"].fillna(0) + merged["sz"].fillna(0)) / 1e4  # 万元→亿元
        merged = merged[["date", "value"]].dropna(subset=["value"]).sort_values("date")
        return merged.reset_index(drop=True)

    def market_volume(self):
        """上证指数成交量 (亿股)"""
        self._init_ak()
        df = self._ak.stock_zh_index_daily(symbol="sh000001")
        df = df[["date", "volume"]].copy()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce") / 1e8  # 股→亿股
        return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)

    def new_investors(self):
        """A股新增投资者数量 (万户)"""
        self._init_ak()
        df = self._ak.stock_account_statistics_em()
        return _extract(df, date_col="数据日期", value_col="新增投资者-数量")

    def bond_yield_10y(self):
        """中国10年期国债收益率 (%)"""
        self._init_ak()
        df = self._ak.bond_zh_us_rate()
        return _extract(df, date_col="日期", value_col="中国国债收益率10年")

    def cny_usd(self):
        """人民币汇率中间价 (USD/CNY)"""
        self._init_ak()
        df = self._ak.currency_boc_safe()
        return _extract(df, date_col="日期", value_col="美元")

    def caixin_pmi(self):
        """财新制造业 PMI"""
        self._init_ak()
        df = self._ak.macro_china_cx_pmi_yearly()
        return _from_financial_calendar(df)

    def enterprise_boom(self):
        """企业景气指数"""
        self._init_ak()
        df = self._ak.macro_china_enterprise_boom_index()
        return _extract(df, date_col="季度", value_col="企业景气指数-指数")

    def shibor_3m(self):
        """Shibor 3个月利率 (%)"""
        self._init_ak()
        df = self._ak.rate_interbank(
            market="上海银行同业拆借市场",
            symbol="Shibor人民币",
            indicator="3月",
        )
        return _extract(df, date_col="报告日", value_col="利率")

    def reserve_ratio(self):
        """存款准备金率 — 大型金融机构 (%)"""
        self._init_ak()
        df = self._ak.macro_china_reserve_requirement_ratio()
        df = df[["生效时间", "大型金融机构-调整后"]].copy()
        df.columns = ["date", "value"]
        df["date"] = _parse_date_series(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


def _from_financial_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize financial calendar format: 商品, 日期, 今值, 预测值, 前值."""
    df = df[["日期", "今值"]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


def _extract(df: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    """Generic extract: pick date and value columns, parse dates."""
    # Find matching columns
    actual_date = date_col
    if date_col not in df.columns:
        for c in df.columns:
            if c.strip() == date_col:
                actual_date = c
                break
    actual_value = value_col
    if value_col not in df.columns:
        for c in df.columns:
            if value_col in c:
                actual_value = c
                break

    df = df[[actual_date, actual_value]].copy()
    df.columns = ["date", "value"]
    df["date"] = _parse_date_series(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


def _parse_date_series(series: pd.Series) -> pd.Series:
    """Parse Chinese-format dates like '2026年05月份', '2026年第1季度', '2003.12'."""
    s = series.astype(str).str.strip()
    try:
        return pd.to_datetime(s)
    except Exception:
        pass
    for fmt in _DATE_FORMATS:
        try:
            result = pd.to_datetime(s, format=fmt, errors="coerce")
            if result.notna().sum() > len(s) * 0.5:
                return result
        except Exception:
            continue
    return pd.to_datetime(s, errors="coerce")


def _parse_quarter(s: str) -> str:
    """Parse '2026年第1季度' → '2026-01-01' (Q1→Jan, Q2→Apr, Q3→Jul, Q4→Oct)."""
    import re
    s = str(s).strip()
    m = re.match(r"(\d{4})年第(\d)季度", s)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        month = (q - 1) * 3 + 1
        return f"{y}-{month:02d}-01"
    return None


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "value"])


def _clean(df, cols: dict = None, date_col: str = None, value_col: str = None):
    """Legacy compatibility stub."""
    if date_col and value_col:
        return _extract(df, date_col, value_col)
    if cols:
        df = df.rename(columns=cols)
    return df
