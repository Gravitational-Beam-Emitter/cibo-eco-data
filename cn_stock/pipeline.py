"""
Data pipeline — fetch daily limit-up stocks from AKShare and enrich with LLM tags.

Usage:
    python -m cn_stock.pipeline              # fetch latest trading day
    python -m cn_stock.pipeline --date 20260612  # fetch specific date
    python -m cn_stock.pipeline --no-llm     # skip LLM tagging
    python -m cn_stock.pipeline --all        # fetch last 7 trading days
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from cn_stock.storage import (
    init_db,
    upsert_limit_up_stocks,
    upsert_stock_reasons,
    upsert_daily_narratives,
)
from cn_stock.tagging import tag_stocks, generate_narratives, needs_llm

logger = logging.getLogger("cn_stock.pipeline")


def fetch_daily(date: str, use_llm: bool = True, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Fetch and store limit-up data for one trading day.

    Args:
        date: Trading date in YYYYMMDD format
        use_llm: Whether to call Claude API for reason tagging
        db_path: Optional DuckDB path override

    Returns:
        Summary dict with counts
    """
    import akshare as ak

    summary = {"date": date, "zt_count": 0, "strong_count": 0, "tagged": 0, "narratives": 0, "errors": []}

    conn = init_db(db_path)

    try:
        # 1. Fetch basic limit-up pool
        try:
            df_zt = ak.stock_zt_pool_em(date=date)
            if not df_zt.empty:
                df_zt["date"] = pd.to_datetime(date)
                # AKShare column mapping
                col_map = {
                    "代码": "code", "名称": "name", "涨跌幅": "pct", "最新价": "price",
                    "成交额": "amount", "流通市值": "ltsz", "总市值": "zsz",
                    "换手率": "hs", "封板资金": "fund", "首次封板时间": "fbt",
                    "最后封板时间": "lbt", "炸板次数": "zbc", "涨停统计": "zttj",
                    "连板数": "lbc", "所属行业": "hybk",
                }
                df_zt = df_zt.rename(columns=col_map)
                # Drop serial number column
                df_zt = df_zt.drop(columns=["序号"], errors="ignore")
                # Ensure numeric types
                for c in ["pct", "price", "hs", "lbc", "zbc"]:
                    if c in df_zt.columns:
                        df_zt[c] = pd.to_numeric(df_zt[c], errors="coerce")
                for c in ["amount", "fund"]:
                    if c in df_zt.columns:
                        df_zt[c] = pd.to_numeric(df_zt[c], errors="coerce").astype("Int64")

                count = upsert_limit_up_stocks(conn, df_zt)
                summary["zt_count"] = count
                logger.info(f"[{date}] {count} limit-up stocks stored")
            else:
                logger.warning(f"[{date}] No limit-up stocks found")

        except Exception as e:
            err = f"AKShare fetch failed: {e}"
            summary["errors"].append(err)
            logger.error(err)

        # 2. Fetch strong pool (for reference)
        try:
            df_strong = ak.stock_zt_pool_strong_em(date=date)
            summary["strong_count"] = len(df_strong)
            logger.info(f"[{date}] {len(df_strong)} strong-pool stocks")
        except Exception as e:
            logger.warning(f"[{date}] Strong pool fetch failed: {e}")

        # 3. LLM tagging (if enabled and available)
        if use_llm and needs_llm():
            try:
                df_stocks = df_zt.copy()  # type: ignore
                if not df_stocks.empty:
                    # Tag individual stocks
                    reasons = tag_stocks(df_stocks)
                    if reasons:
                        upsert_stock_reasons(conn, date, reasons)
                        summary["tagged"] = len(reasons)
                        logger.info(f"[{date}] {len(reasons)} stocks tagged")

                    # Generate narratives
                    narratives = generate_narratives(df_stocks)
                    if narratives:
                        upsert_daily_narratives(conn, date, narratives)
                        summary["narratives"] = len(narratives)
                        logger.info(f"[{date}] {len(narratives)} narratives generated")
            except Exception as e:
                err = f"LLM tagging failed: {e}"
                summary["errors"].append(err)
                logger.error(err)
        elif use_llm:
            logger.info(f"[{date}] LLM tagging skipped — no API key configured")

    finally:
        conn.close()

    return summary


def fetch_latest(use_llm: bool = True, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Fetch the most recent trading day's data."""
    import akshare as ak
    try:
        # Get latest trading day from AKShare
        today = datetime.now()
        # Try today, then yesterday, then day before
        for offset in range(10):
            d = (today - timedelta(days=offset)).strftime("%Y%m%d")
            try:
                df = ak.stock_zt_pool_em(date=d)
                if not df.empty:
                    logger.info(f"Found data for {d}")
                    return fetch_daily(d, use_llm=use_llm, db_path=db_path)
            except Exception:
                continue
        return {"error": "No trading data found in last 10 days"}
    except Exception as e:
        return {"error": str(e)}


def fetch_batch(dates: list[str], use_llm: bool = True, db_path: Optional[str] = None) -> list[Dict[str, Any]]:
    """Fetch multiple dates."""
    results = []
    for d in dates:
        results.append(fetch_daily(d, use_llm=use_llm, db_path=db_path))
        time.sleep(1)  # Be nice to AKShare
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if "--no-llm" in sys.argv:
        use_llm = False
    else:
        use_llm = True

    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        date = sys.argv[idx + 1]
        result = fetch_daily(date, use_llm=use_llm)
        print(f"\nResult: {result}")
    elif "--all" in sys.argv:
        # Fetch last 7 trading days
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(10)]
        use_llm_flag = not any(x in sys.argv for x in ["--no-llm"])
        results = fetch_batch(dates, use_llm=use_llm_flag)
        for r in results:
            print(f"  {r}")
    else:
        result = fetch_latest(use_llm=use_llm)
        print(f"\nResult: {result}")
