"""
REST API — FastAPI server exposing macroeconomic data.

Start with:  uvicorn app.api:app --reload
OpenAPI docs: http://localhost:8000/docs
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from app.config import FRED_API_KEY, EIA_API_KEY
from app.storage import (
    init_db,
    get_indicators,
    get_indicator,
    get_data,
    search_indicators,
    get_all_tags,
    get_indicators_by_tag,
)
from app.pipeline import run_once

app = FastAPI(
    title="Eco Data API",
    description="Unified macroeconomic data access — 21 sources: FRED, AKShare, World Bank, BoJ, EIA, GitHub, HuggingFace, DeFi Llama, Polymarket, CoinGecko, AI Infrastructure, AI Company Financials, and more.",
    version="1.1.0",
)

# ── Startup ──────────────────────────────────────────────────


@app.on_event("startup")
def _startup():
    init_db()  # ensure tables exist


# ── Indicators ───────────────────────────────────────────────


@app.get("/api/v1/indicators")
def list_indicators(
    source: Optional[str] = Query(None, description="Filter by source: us, cn, global_, hk, jp, euro, uk, de, au, ca, ch, bond, futures, shipping, banks, alt, llm, defi, energy, ai, ai_co"),
    tag: Optional[str] = Query(None, description="Filter by tag (e.g. 通胀, 就业, AI算力, 数据中心)"),
):
    """List all available indicators with metadata. Filter by source and/or tag."""
    conn = init_db()
    try:
        if tag:
            df = get_indicators_by_tag(conn, tag)
        else:
            df = get_indicators(conn, source=source)
        return _df_to_list(df)
    finally:
        conn.close()


@app.get("/api/v1/indicators/search")
def search_indicators_api(q: str = Query(..., description="Search query")):
    """Search indicators by keyword (name, description, tags, or source)."""
    conn = init_db()
    try:
        df = search_indicators(conn, q)
        return _df_to_list(df)
    finally:
        conn.close()


@app.get("/api/v1/tags")
def list_tags():
    """List all tags with indicator counts. Browse data by topic without knowing keywords."""
    conn = init_db()
    try:
        return get_all_tags(conn)
    finally:
        conn.close()


@app.get("/api/v1/indicators/{indicator_id}")
def get_indicator_detail(indicator_id: int):
    """Get a single indicator's metadata."""
    conn = init_db()
    try:
        row = get_indicator(conn, indicator_id)
        if row is None:
            raise HTTPException(404, f"Indicator {indicator_id} not found")
        # Parse params JSON
        if isinstance(row.get("params"), str):
            import json
            try:
                row["params"] = json.loads(row["params"])
            except (json.JSONDecodeError, TypeError):
                pass
        # Convert timestamp
        if row.get("last_updated"):
            row["last_updated"] = str(row["last_updated"])
        return row
    finally:
        conn.close()


# ── Data ─────────────────────────────────────────────────────


@app.get("/api/v1/data/{indicator_id}")
def query_data(
    indicator_id: int,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(1000, ge=1, le=50000, description="Max rows to return"),
):
    """Query time-series data for an indicator."""
    conn = init_db()
    try:
        # Verify indicator exists
        meta = get_indicator(conn, indicator_id)
        if meta is None:
            raise HTTPException(404, f"Indicator {indicator_id} not found")

        df = get_data(conn, indicator_id, start=start, end=end, limit=limit)
        return {
            "indicator": meta,
            "count": len(df),
            "data": _df_to_records(df),
        }
    finally:
        conn.close()


@app.get("/api/v1/data/{indicator_id}/latest")
def latest_value(indicator_id: int):
    """Get the most recent observation for an indicator."""
    conn = init_db()
    try:
        meta = get_indicator(conn, indicator_id)
        if meta is None:
            raise HTTPException(404, f"Indicator {indicator_id} not found")

        df = get_data(conn, indicator_id, limit=1)
        if df.empty:
            return {"indicator": meta, "latest": None}
        return {
            "indicator": meta,
            "latest": {"date": str(df.iloc[0]["date"]), "value": df.iloc[0]["value"]},
        }
    finally:
        conn.close()


# ── Fetch ────────────────────────────────────────────────────


@app.post("/api/v1/fetch")
def trigger_fetch(
    source: Optional[str] = Query(None, description="Limit to one source (us, cn, global_, hk, jp, euro, uk, de, au, ca, ch, bond, futures, shipping, banks, alt, llm, defi, energy, ai, ai_co)"),
):
    """Trigger a data fetch. Without source=, fetches all."""
    sources = [source] if source else None
    summary = run_once(sources=sources)
    return summary


# ── Health ───────────────────────────────────────────────────


@app.get("/api/v1/health")
def health():
    """Service health check."""
    conn = init_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
        obs_count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        return {
            "status": "ok",
            "indicators": count,
            "observations": obs_count,
        }
    finally:
        conn.close()


# ── Helpers ──────────────────────────────────────────────────


def _df_to_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert DataFrame to list of dicts, converting types for JSON."""
    records = df.to_dict(orient="records")
    for r in records:
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                r[k] = str(v)
            elif pd.isna(v):
                r[k] = None
        # Parse params JSON string
        if "params" in r and isinstance(r["params"], str):
            import json
            try:
                r["params"] = json.loads(r["params"])
            except (json.JSONDecodeError, TypeError):
                pass
    return records


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert observations DataFrame to JSON-serializable records."""
    records = []
    for _, row in df.iterrows():
        records.append({
            "date": str(row["date"]),
            "value": row["value"],
        })
    return records
