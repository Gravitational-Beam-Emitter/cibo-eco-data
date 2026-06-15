"""
Storage layer — DuckDB-backed time-series store for macroeconomic indicators.

Tables:
  indicators   — metadata for each data series
  observations — individual data points (indicator_id, date, value)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = Path(os.environ.get("ECO_DATA_DB", Path(__file__).resolve().parent.parent / "eco_data.duckdb"))


def _conn(db_path: str | Path | None = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = str(db_path or DB_PATH)
    return duckdb.connect(path, read_only=read_only)


def init_db(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Create tables if they don't exist. Returns connection for chaining."""
    conn = _conn(db_path)
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_indicators_id")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_indicators_id'),
            source VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            method VARCHAR NOT NULL,
            params VARCHAR NOT NULL DEFAULT '{}',
            description VARCHAR,
            frequency VARCHAR,
            last_updated TIMESTAMP,
            UNIQUE(source, method, params)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            indicator_id INTEGER NOT NULL,
            date DATE NOT NULL,
            value DOUBLE NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(indicator_id, date),
            FOREIGN KEY(indicator_id) REFERENCES indicators(id)
        )
    """)
    # Index for range queries
    conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_date ON observations(indicator_id, date)")
    return conn


def upsert_indicator(conn: duckdb.DuckDBPyConnection, indicator: dict) -> int:
    """Insert or update an indicator, return its id."""
    params_json = json.dumps(indicator.get("params", {}), ensure_ascii=False)
    # SELECT first to avoid DuckDB FK constraint issue with ON CONFLICT
    existing = conn.execute(
        "SELECT id FROM indicators WHERE source=? AND method=? AND params=?",
        [indicator["source"], indicator["method"], params_json]
    ).fetchone()
    if existing:
        indicator_id = existing[0]
        conn.execute(
            "UPDATE indicators SET name=?, description=?, frequency=? WHERE id=?",
            [indicator["name"], indicator.get("description", ""), indicator.get("frequency", ""), indicator_id]
        )
        return indicator_id
    result = conn.execute(
        "INSERT INTO indicators (source, name, method, params, description, frequency) VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
        [indicator["source"], indicator["name"], indicator["method"], params_json, indicator.get("description", ""), indicator.get("frequency", "")]
    )
    return result.fetchone()[0]


def upsert_observations(
    conn: duckdb.DuckDBPyConnection,
    indicator_id: int,
    df: pd.DataFrame,
    *,
    date_col: str = "date",
    value_col: str = "value",
) -> int:
    """Write observation rows from a DataFrame. Skips duplicates. Returns row count inserted."""
    if df.empty:
        return 0
    # Ensure correct column names
    df = df[[date_col, value_col]].copy()
    df.columns = ["date", "value"]
    df["indicator_id"] = indicator_id

    # Register temp view and INSERT … ON CONFLICT
    conn.register("_tmp_obs", df)
    rows = conn.execute("""
        INSERT INTO observations (indicator_id, date, value)
        SELECT indicator_id, date, value FROM _tmp_obs
        ON CONFLICT (indicator_id, date) DO UPDATE SET
            value = excluded.value,
            fetched_at = now()
    """).fetchall()
    conn.unregister("_tmp_obs")
    count = rows[0][0] if rows else 0

    # Update last_updated timestamp
    conn.execute("UPDATE indicators SET last_updated = now() WHERE id = ?", [indicator_id])
    return count


def mark_indicator_updated(conn: duckdb.DuckDBPyConnection, indicator_id: int) -> None:
    conn.execute("UPDATE indicators SET last_updated = now() WHERE id = ?", [indicator_id])


def get_indicators(conn: duckdb.DuckDBPyConnection, source: str | None = None) -> pd.DataFrame:
    """Return all indicators, optionally filtered by source."""
    if source:
        return conn.execute(
            "SELECT * FROM indicators WHERE source = ? ORDER BY id", [source]
        ).df()
    return conn.execute("SELECT * FROM indicators ORDER BY source, id").df()


def get_indicator(conn: duckdb.DuckDBPyConnection, indicator_id: int) -> dict | None:
    """Return a single indicator as dict, or None."""
    row = conn.execute(
        "SELECT * FROM indicators WHERE id = ?", [indicator_id]
    ).fetchone()
    if row is None:
        return None
    cols = [desc[0] for desc in conn.description]
    return dict(zip(cols, row))


def get_data(
    conn: duckdb.DuckDBPyConnection,
    indicator_id: int,
    start: str | None = None,
    end: str | None = None,
    limit: int = 10000,
) -> pd.DataFrame:
    """Query observation data for an indicator, with optional date range."""
    sql = "SELECT date, value FROM observations WHERE indicator_id = ?"
    params = [indicator_id]
    if start:
        sql += " AND date >= ?"
        params.append(start)
    if end:
        sql += " AND date <= ?"
        params.append(end)
    sql += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).df()


def search_indicators(conn: duckdb.DuckDBPyConnection, query: str) -> pd.DataFrame:
    """Full-text-like search across indicator name and description."""
    pattern = f"%{query}%"
    return conn.execute("""
        SELECT * FROM indicators
        WHERE name ILIKE ? OR description ILIKE ? OR source ILIKE ?
        ORDER BY source, id
    """, [pattern, pattern, pattern]).df()


def observation_count(conn: duckdb.DuckDBPyConnection, indicator_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM observations WHERE indicator_id = ?", [indicator_id]
    ).fetchone()
    return row[0] if row else 0
