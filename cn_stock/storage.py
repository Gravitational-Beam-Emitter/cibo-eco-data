"""
Storage layer — DuckDB-backed store for daily limit-up stock data.

Tables:
  limit_up_stocks   — daily limit-up stocks from AKShare
  stock_reasons     — LLM-generated reason tags per stock
  daily_narratives  — LLM-generated market narratives per day
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd

from cn_stock.config import DB_PATH


def _norm_date(date: str) -> str:
    """Normalize date string to YYYY-MM-DD for DuckDB."""
    date = date.replace("-", "").replace("/", "")
    if len(date) == 8:
        return f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    return date


def _conn(db_path: Optional[str] = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = db_path or DB_PATH
    return duckdb.connect(path, read_only=read_only)


def init_db(db_path: Optional[str] = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Create tables if they don't exist. Returns connection for chaining."""
    conn = _conn(db_path, read_only=read_only)
    if read_only:
        return conn
    conn.execute("""
        CREATE TABLE IF NOT EXISTS limit_up_stocks (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            price DOUBLE,
            pct DOUBLE,
            amount BIGINT,
            ltsz DOUBLE,
            zsz DOUBLE,
            hs DOUBLE,
            fund BIGINT,
            fbt VARCHAR,
            lbt VARCHAR,
            zbc INTEGER,
            zttj VARCHAR,
            lbc INTEGER,
            hybk VARCHAR,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(date, code)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_reasons (
            date DATE NOT NULL,
            code VARCHAR NOT NULL,
            reasons VARCHAR NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(date, code)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_narratives (
            date DATE NOT NULL,
            tag VARCHAR NOT NULL DEFAULT '',
            name VARCHAR NOT NULL,
            description TEXT,
            stocks_json VARCHAR NOT NULL DEFAULT '[]',
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(date, name)
        )
    """)
    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lus_date ON limit_up_stocks(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lus_code ON limit_up_stocks(code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lus_hybk ON limit_up_stocks(hybk)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sr_date ON stock_reasons(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dn_date ON daily_narratives(date)")
    return conn


def upsert_limit_up_stocks(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Batch insert/update limit-up stocks. Returns row count."""
    if df.empty:
        return 0

    needed = ["date", "code", "name", "price", "pct", "amount", "ltsz", "zsz",
              "hs", "fund", "fbt", "lbt", "zbc", "zttj", "lbc", "hybk"]
    for col in needed:
        if col not in df.columns:
            df[col] = None

    sub = df[needed].copy()

    conn.register("_tmp_lus", sub)
    rows = conn.execute("""
        INSERT INTO limit_up_stocks (date, code, name, price, pct, amount, ltsz, zsz,
                                     hs, fund, fbt, lbt, zbc, zttj, lbc, hybk)
        SELECT date, code, name, price, pct, amount, ltsz, zsz,
               hs, fund, fbt, lbt, zbc, zttj, lbc, hybk
        FROM _tmp_lus
        ON CONFLICT (date, code) DO UPDATE SET
            name = excluded.name,
            price = excluded.price,
            pct = excluded.pct,
            amount = excluded.amount,
            ltsz = excluded.ltsz,
            zsz = excluded.zsz,
            hs = excluded.hs,
            fund = excluded.fund,
            fbt = excluded.fbt,
            lbt = excluded.lbt,
            zbc = excluded.zbc,
            zttj = excluded.zttj,
            lbc = excluded.lbc,
            hybk = excluded.hybk,
            fetched_at = now()
    """).fetchall()
    conn.unregister("_tmp_lus")
    return rows[0][0] if rows else 0


def upsert_stock_reasons(conn: duckdb.DuckDBPyConnection, date: str, reasons: List[Dict[str, str]]) -> int:
    """Insert or update LLM-generated stock reason tags. Returns row count."""
    if not reasons:
        return 0
    df = pd.DataFrame(reasons)
    df["date"] = pd.to_datetime(_norm_date(date))
    conn.register("_tmp_sr", df[["date", "code", "reasons"]])
    rows = conn.execute("""
        INSERT INTO stock_reasons (date, code, reasons)
        SELECT date, code, reasons FROM _tmp_sr
        ON CONFLICT (date, code) DO UPDATE SET
            reasons = excluded.reasons,
            generated_at = now()
    """).fetchall()
    conn.unregister("_tmp_sr")
    return rows[0][0] if rows else 0


def upsert_daily_narratives(conn: duckdb.DuckDBPyConnection, date: str, narratives: List[Dict[str, Any]]) -> int:
    """Insert or update LLM-generated daily narratives. Returns row count."""
    if not narratives:
        return 0
    count = 0
    for n in narratives:
        stocks_json = json.dumps(n.get("stocks", []), ensure_ascii=False)
        conn.execute("""
            INSERT INTO daily_narratives (date, tag, name, description, stocks_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (date, name) DO UPDATE SET
                tag = excluded.tag,
                description = excluded.description,
                stocks_json = excluded.stocks_json,
                generated_at = now()
        """, [_norm_date(date), n.get("tag", ""), n["name"], n.get("description", ""), stocks_json])
        count += 1
    return count


def get_daily_stocks(conn: duckdb.DuckDBPyConnection, date: str) -> pd.DataFrame:
    """Get limit-up stocks for a date, with LLM reasons if available."""
    return conn.execute("""
        SELECT s.*, r.reasons
        FROM limit_up_stocks s
        LEFT JOIN stock_reasons r ON s.date = r.date AND s.code = r.code
        WHERE s.date = ?
        ORDER BY s.lbc DESC, s.pct DESC
    """, [_norm_date(date)]).df()


def get_stock_history(conn: duckdb.DuckDBPyConnection, code: str, limit: int = 60) -> pd.DataFrame:
    """Get limit-up history for a specific stock."""
    return conn.execute("""
        SELECT s.*, r.reasons
        FROM limit_up_stocks s
        LEFT JOIN stock_reasons r ON s.date = r.date AND s.code = r.code
        WHERE s.code = ?
        ORDER BY s.date DESC
        LIMIT ?
    """, [code, limit]).df()


def get_narratives(conn: duckdb.DuckDBPyConnection, date: str) -> List[Dict[str, Any]]:
    """Get daily market narratives."""
    rows = conn.execute("""
        SELECT date, tag, name, description, stocks_json
        FROM daily_narratives
        WHERE date = ?
        ORDER BY name
    """, [_norm_date(date)]).fetchall()
    result = []
    for row in rows:
        result.append({
            "date": str(row[0]),
            "tag": row[1],
            "name": row[2],
            "description": row[3],
            "stocks": json.loads(row[4]),
        })
    return result


def get_industry_summary(conn: duckdb.DuckDBPyConnection, date: str) -> pd.DataFrame:
    """Get industry distribution for a date."""
    return conn.execute("""
        SELECT hybk AS industry, COUNT(*) AS count,
               AVG(pct) AS avg_pct, MAX(lbc) AS max_lbc
        FROM limit_up_stocks
        WHERE date = ?
        GROUP BY hybk
        ORDER BY count DESC
    """, [_norm_date(date)]).df()


def get_available_dates(conn: duckdb.DuckDBPyConnection, limit: int = 30) -> List[str]:
    """Get list of dates with data."""
    rows = conn.execute("""
        SELECT DISTINCT date FROM limit_up_stocks
        ORDER BY date DESC LIMIT ?
    """, [limit]).fetchall()
    return [str(r[0]) for r in rows]


def get_daily_summary(conn: duckdb.DuckDBPyConnection, date: str) -> Dict[str, Any]:
    """Get a summary for a trading day."""
    row = conn.execute("""
        SELECT
            COUNT(*) AS zt_count,
            AVG(pct) AS avg_pct,
            MAX(lbc) AS max_lbc,
            SUM(CASE WHEN zbc > 0 THEN 1 ELSE 0 END) AS zb_count,
            COUNT(DISTINCT hybk) AS sector_count
        FROM limit_up_stocks
        WHERE date = ?
    """, [_norm_date(date)]).fetchone()
    if row is None or row[0] == 0:
        return {"date": date, "zt_count": 0}
    return {
        "date": date,
        "zt_count": int(row[0]),
        "avg_pct": round(float(row[1]), 2),
        "max_lbc": int(row[2]) if row[2] else 0,
        "zb_count": int(row[3]),
        "sector_count": int(row[4]),
    }
