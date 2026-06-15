"""
FastAPI REST API — serve daily limit-up stock review data.

Usage:
    python -m uvicorn cn_stock.api:app --host 127.0.0.1 --port 8001

Endpoints:
    GET  /api/v1/daily/{date}       — Full daily review (stocks + tags + narratives + summary)
    GET  /api/v1/stocks/{date}      — Limit-up stocks for a date (with reasons)
    GET  /api/v1/stock/{code}       — Stock limit-up history
    GET  /api/v1/narratives/{date}  — Market narratives
    GET  /api/v1/industry/{date}    — Industry distribution
    GET  /api/v1/dates              — Available trading dates
    POST /api/v1/fetch?date=        — Trigger data fetch (+ LLM tagging)
    GET  /api/v1/health             — Service health
"""

from __future__ import annotations

import logging
from datetime import date as date_type
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from cn_stock.storage import (
    init_db,
    get_daily_stocks,
    get_stock_history,
    get_narratives,
    get_industry_summary,
    get_available_dates,
    get_daily_summary,
)
from cn_stock.pipeline import fetch_daily

logger = logging.getLogger("cn_stock.api")

app = FastAPI(
    title="A股涨停复盘 API",
    description="中国A股每日涨停板数据 + LLM 标签 + 市场主线分析",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────────

@app.get("/api/v1/health")
def health():
    conn = init_db()
    try:
        row = conn.execute("SELECT COUNT(*) FROM limit_up_stocks").fetchone()
        count = row[0] if row else 0
        row2 = conn.execute("SELECT COUNT(DISTINCT date) FROM limit_up_stocks").fetchone()
        days = row2[0] if row2 else 0
        return {
            "status": "ok",
            "total_stocks": count,
            "trading_days": days,
        }
    finally:
        conn.close()


# ── Daily Review ────────────────────────────────────────────

@app.get("/api/v1/daily/{date}")
def daily_review(date: str):
    """Full daily review: stocks, narratives, summary, industry breakdown."""
    conn = init_db(read_only=True)
    try:
        stocks_df = get_daily_stocks(conn, date)
        if stocks_df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {date}")

        narratives = get_narratives(conn, date)
        summary = get_daily_summary(conn, date)
        industry_df = get_industry_summary(conn, date)

        return {
            "date": date,
            "summary": summary,
            "stocks": stocks_df.to_dict(orient="records"),
            "narratives": narratives,
            "industries": industry_df.to_dict(orient="records"),
        }
    finally:
        conn.close()


# ── Stocks ──────────────────────────────────────────────────

@app.get("/api/v1/stocks/{date}")
def stocks_by_date(date: str, industry: Optional[str] = None):
    """List limit-up stocks for a date. Optional industry filter."""
    conn = init_db(read_only=True)
    try:
        stocks_df = get_daily_stocks(conn, date)
        if stocks_df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {date}")
        if industry:
            stocks_df = stocks_df[stocks_df["hybk"] == industry]
        return {"date": date, "count": len(stocks_df), "stocks": stocks_df.to_dict(orient="records")}
    finally:
        conn.close()


@app.get("/api/v1/stock/{code}")
def stock_history(code: str, limit: int = Query(default=60, le=200)):
    """Limit-up history for a specific stock."""
    conn = init_db(read_only=True)
    try:
        df = get_stock_history(conn, code, limit=limit)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No history for {code}")
        return {"code": code, "count": len(df), "history": df.to_dict(orient="records")}
    finally:
        conn.close()


# ── Narratives ──────────────────────────────────────────────

@app.get("/api/v1/narratives/{date}")
def narratives_by_date(date: str):
    """Get market narratives for a date."""
    conn = init_db(read_only=True)
    try:
        narratives = get_narratives(conn, date)
        return {"date": date, "narratives": narratives}
    finally:
        conn.close()


# ── Industry ────────────────────────────────────────────────

@app.get("/api/v1/industry/{date}")
def industry_breakdown(date: str):
    """Get industry distribution for a date."""
    conn = init_db(read_only=True)
    try:
        df = get_industry_summary(conn, date)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {date}")
        return {"date": date, "industries": df.to_dict(orient="records")}
    finally:
        conn.close()


# ── Dates ───────────────────────────────────────────────────

@app.get("/api/v1/dates")
def available_dates(limit: int = Query(default=30, le=60)):
    """Get list of available trading dates."""
    conn = init_db(read_only=True)
    try:
        dates = get_available_dates(conn, limit=limit)
        return {"count": len(dates), "dates": dates}
    finally:
        conn.close()


# ── Fetch ───────────────────────────────────────────────────

@app.post("/api/v1/fetch")
def trigger_fetch(date: Optional[str] = None, llm: bool = True):
    """Manually trigger data fetch for a date (defaults to latest)."""
    from cn_stock.pipeline import fetch_latest as _fetch_latest
    if date:
        result = fetch_daily(date, use_llm=llm)
    else:
        result = _fetch_latest(use_llm=llm)
    return {"status": "completed", "result": result}


# ── Startup ─────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    logger.info("cn_stock API started")
