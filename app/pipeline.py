"""
Data pipeline — fetch macroeconomic indicators and persist to DuckDB.

Supports one-shot runs and scheduled background execution via APScheduler.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

from app.eco_harness import EcoHarness
from app.storage import init_db, upsert_indicator, upsert_observations, mark_indicator_updated
from app.indicators_registry import INDICATORS, requires_api_key

logger = logging.getLogger("eco_data.pipeline")


class Pipeline:
    """Fetches indicators via EcoHarness and persists to DuckDB."""

    def __init__(self, eh: EcoHarness, db_path: Optional[str] = None):
        self.eh = eh
        self.db_path = db_path
        self._indicator_cache: Dict[str, int] = {}  # "source.method:params" → id

    def run(self, sources: Optional[list[str]] = None, frequencies: Optional[list[str]] = None,
            dry_run: bool = False) -> dict:
        """Fetch all registered indicators. Returns summary dict.

        sources: limit to specific sources, e.g. ['cn', 'jp']. None = all.
        frequencies: limit by frequency, e.g. ['daily', 'monthly']. None = all.
        dry_run: resolve indicators but don't fetch or store.
        """
        conn = init_db(self.db_path)
        summary: dict[str, Any] = {"total": 0, "success": 0, "skipped": 0, "failed": 0, "rows": 0, "errors": []}

        try:
            for ind in INDICATORS:
                src = ind["source"]
                if sources and src not in sources:
                    continue
                if frequencies and ind.get("frequency") not in frequencies:
                    continue
                summary["total"] += 1

                # Check API key requirement
                needed_key = requires_api_key(src, ind["method"])
                if needed_key == "FRED" and not self.eh.us._fred_key:
                    summary["skipped"] += 1
                    logger.info(f"SKIP {src}.{ind['method']} — no FRED_API_KEY")
                    continue
                if needed_key == "EIA" and not self.eh.energy._key:
                    summary["skipped"] += 1
                    logger.info(f"SKIP {src}.{ind['method']} — no EIA_API_KEY")
                    continue

                if dry_run:
                    summary["success"] += 1
                    logger.info(f"DRY-RUN {src}.{ind['method']}({ind['params']})")
                    continue

                try:
                    indicator_id = self._fetch_one(conn, ind)
                    summary["success"] += 1
                    summary["rows"] += indicator_id
                except Exception as e:
                    summary["failed"] += 1
                    err_msg = f"{src}.{ind['method']}: {e}"
                    summary["errors"].append(err_msg)
                    logger.warning(f"FAIL {err_msg}")
        finally:
            conn.close()

        return summary

    def _fetch_one(self, conn, ind: dict) -> int:
        """Fetch a single indicator, store it, return observation count."""
        source = ind["source"]
        method_name = ind["method"]
        params: dict = ind.get("params", {})

        # Resolve the harness sub-object
        source_attr = "global_" if source == "global_" else source
        sub = getattr(self.eh, source_attr)
        if sub is None:
            logger.info(f"SKIP {source}.{method_name} — harness not available")
            return 0

        # Call the method with params (e.g. gdp(country='CHN'))
        method = getattr(sub, method_name)
        if params:
            df = method(**params)
        else:
            df = method()

        # Normalize to date/value columns if needed
        df = _normalize(df, source)
        # Drop NaNs (FRED returns NaN for weekends/holidays)
        df = df.dropna(subset=["value"])

        if df.empty:
            logger.info(f"EMPTY {source}.{method_name}")
            return 0

        # Upsert indicator metadata
        indicator_id = upsert_indicator(conn, ind)

        # Upsert observations
        count = upsert_observations(conn, indicator_id, df)
        logger.info(f"OK {source}.{method_name} — {count} rows (id={indicator_id})")
        return count

    def run_sources(self, sources: list[str]) -> dict:
        """Fetch only specified sources."""
        return self.run(sources=sources)


def _normalize(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Normalize DataFrame to standard [date, value] columns."""
    if df.empty:
        return df

    # Already has date/value columns
    if set(df.columns) >= {"date", "value"}:
        return _safe_date_value(df[["date", "value"]])

    # World Bank returns wide-format DataFrames (countries as columns)
    if source == "global_":
        return _normalize_wb(df)

    # EIA / energy: period + value columns (value may be string)
    if "period" in df.columns and "value" in df.columns:
        df = df[["period", "value"]].copy()
        df.columns = ["date", "value"]
        return _safe_date_value(df)

    # Try to auto-detect date and value columns
    date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower() or "period" in c.lower()]
    value_cols = [c for c in df.columns
                  if c not in date_cols and df[c].dtype in ("float64", "int64", "float32", "int32", "object")]
    if date_cols and value_cols:
        df = df[[date_cols[0], value_cols[0]]].copy()
        df.columns = ["date", "value"]
        return _safe_date_value(df)

    return df


def _safe_date_value(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure value is numeric and date is datetime."""
    df = df.copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _normalize_wb(df: pd.DataFrame) -> pd.DataFrame:
    """Convert World Bank wide-format DataFrame to long [date, value]."""
    # wbgapi returns DataFrames with years as columns, series as rows
    # e.g. index=['CHN'], columns=['YR2019','YR2020',...]
    records = []
    for idx, row in df.iterrows():
        for col in df.columns:
            try:
                year = int(str(col).replace("YR", ""))
                val = float(row[col])
                records.append({"date": f"{year}-01-01", "value": val})
            except (ValueError, KeyError):
                continue
    result = pd.DataFrame(records)
    if not result.empty:
        result["date"] = pd.to_datetime(result["date"])
        result = result.sort_values("date").reset_index(drop=True)
    return result


class Scheduler:
    """Tiered APScheduler — daily / weekly / monthly pipelines.

    Tier 1 (daily):    daily-frequency indicators (treasury yields, BDI)
    Tier 2 (weekly):    daily + weekly-frequency (crude oil)
    Tier 3 (monthly):   all indicators (monthly CPI/PMI/GDP etc.)
    """

    # Cron: minute-of-hour chosen to avoid :00/:30 contention
    FREQ_CRON = {
        "daily":   ("7 8 * * *",     ["daily"]),                    # 8:07 AM every day
        "weekly":  ("13 8 * * 1",    ["daily", "weekly"]),          # 8:13 AM every Monday
        "monthly": ("21 8 15 * *",   ["daily", "weekly", "monthly", "quarterly", "yearly"]),  # 8:21 AM on 15th
    }

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self._scheduler: Optional[BackgroundScheduler] = None

    def start(self) -> BackgroundScheduler:
        self._scheduler = BackgroundScheduler()
        for tier, (cron_expr, freqs) in self.FREQ_CRON.items():
            self._scheduler.add_job(
                lambda f=freqs: self._run(f),
                "cron",
                **self._parse_cron(cron_expr),
                id=f"eco_fetch_{tier}",
                name=f"EcoData {tier} fetch ({cron_expr})",
            )
            logger.info(f"Registered {tier} job: {cron_expr} → {freqs}")
        self._scheduler.start()
        logger.info("Tiered scheduler started (daily + weekly + monthly)")
        return self._scheduler

    def stop(self) -> None:
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            logger.info("Pipeline scheduler stopped")

    def _run(self, frequencies: list[str]) -> None:
        logger.info(f"Scheduled fetch for frequencies: {frequencies}")
        start = time.time()
        summary = self.pipeline.run(frequencies=frequencies)
        elapsed = time.time() - start
        logger.info(f"Fetch done in {elapsed:.1f}s — {summary}")

    @staticmethod
    def _parse_cron(cron: str) -> dict:
        parts = cron.strip().split()
        names = ["minute", "hour", "day", "month", "day_of_week"]
        return {names[i]: parts[i] for i in range(min(len(parts), 5))}


def start_scheduler() -> Scheduler:
    """Convenience: create harness + pipeline + scheduler, start all three tiers."""
    from app.config import FRED_API_KEY, EIA_API_KEY
    eh = EcoHarness(fred_api_key=FRED_API_KEY, eia_api_key=EIA_API_KEY)
    pipeline = Pipeline(eh)
    scheduler = Scheduler(pipeline)
    scheduler.start()
    return scheduler


def run_once(
    fred_api_key: str = "",
    eia_api_key: str = "",
    sources: Optional[list[str]] = None,
    frequencies: Optional[list[str]] = None,
    db_path: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Convenience: create harness + pipeline, run once, return summary.

    Keys default to env vars (FRED_API_KEY, EIA_API_KEY) if not provided.
    """
    from app.config import FRED_API_KEY, EIA_API_KEY
    fred_key = fred_api_key or FRED_API_KEY
    eia_key = eia_api_key or EIA_API_KEY
    eh = EcoHarness(fred_api_key=fred_key, eia_api_key=eia_key)
    pipeline = Pipeline(eh, db_path=db_path)
    return pipeline.run(sources=sources, frequencies=frequencies, dry_run=dry_run)
