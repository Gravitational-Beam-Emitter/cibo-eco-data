#!/usr/bin/env python3
"""
Eco Data MCP Server — lightweight MCP implementation over stdio.

Exposes macroeconomic and China stock data as MCP tools for AI agents.
No external MCP SDK needed — implements the JSON-RPC protocol directly.

Claude Code config (~/.claude.json or project .mcp.json):
{
  "mcpServers": {
    "eco-data": {
      "command": "python3",
      "args": ["mcp/eco_data_server.py"],
      "cwd": "/path/to/cibo eco data"
    }
  }
}
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import duckdb

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "eco_data.duckdb")


def _conn():
    return duckdb.connect(DB_PATH, read_only=True)


# ── Tool implementations ──────────────────────────────────────


def tool_list_indicators(source: str = "") -> list[dict]:
    """List all available economic indicators with metadata."""
    conn = _conn()
    try:
        if source:
            rows = conn.execute(
                "SELECT id, source, name, method, description, frequency, last_updated "
                "FROM indicators WHERE source = ? ORDER BY id",
                [source],
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, source, name, method, description, frequency, last_updated "
                "FROM indicators ORDER BY source, id"
            ).fetchall()

        return [
            {
                "id": r[0],
                "source": r[1],
                "name": r[2],
                "method": r[3],
                "description": r[4],
                "frequency": r[5],
                "last_updated": str(r[6]) if r[6] else None,
            }
            for r in rows
        ]
    finally:
        conn.close()


def tool_query_data(
    indicator_id: int,
    start: str = "",
    end: str = "",
    limit: int = 100,
) -> dict:
    """Query time-series observations for a given indicator."""
    conn = _conn()
    try:
        # Get indicator metadata
        meta = conn.execute(
            "SELECT id, source, name, description, frequency FROM indicators WHERE id = ?",
            [indicator_id],
        ).fetchone()
        if not meta:
            return {"error": f"Indicator {indicator_id} not found"}

        # Build query
        sql = "SELECT date, value FROM observations WHERE indicator_id = ?"
        params: list[Any] = [indicator_id]
        if start:
            sql += " AND date >= ?"
            params.append(start)
        if end:
            sql += " AND date <= ?"
            params.append(end)
        sql += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        data = [{"date": str(r[0]), "value": r[1]} for r in rows]

        return {
            "indicator": {
                "id": meta[0],
                "source": meta[1],
                "name": meta[2],
                "description": meta[3],
                "frequency": meta[4],
            },
            "count": len(data),
            "data": data,
        }
    finally:
        conn.close()


def tool_get_latest(indicator_id: int) -> dict:
    """Get the most recent observation for an indicator."""
    return tool_query_data(indicator_id, limit=1)


def tool_search_indicators(query: str) -> list[dict]:
    """Search indicators by keyword in name and description."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, source, name, method, description, frequency FROM indicators "
            "WHERE name ILIKE ? OR description ILIKE ? ORDER BY id",
            [f"%{query}%", f"%{query}%"],
        ).fetchall()
        return [
            {
                "id": r[0],
                "source": r[1],
                "name": r[2],
                "method": r[3],
                "description": r[4],
                "frequency": r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


def tool_data_summary() -> dict:
    """Get a high-level summary of available data."""
    conn = _conn()
    try:
        total_indicators = conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
        total_obs = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        by_source = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM indicators GROUP BY source ORDER BY cnt DESC"
        ).fetchall()
        by_freq = conn.execute(
            "SELECT frequency, COUNT(*) as cnt FROM indicators GROUP BY frequency ORDER BY cnt DESC"
        ).fetchall()
        return {
            "total_indicators": total_indicators,
            "total_observations": total_obs,
            "by_source": [{"source": r[0], "count": r[1]} for r in by_source],
            "by_frequency": [{"frequency": r[0], "count": r[1]} for r in by_freq],
            "data_path": DB_PATH,
        }
    finally:
        conn.close()


def tool_cn_stock_status() -> dict:
    """Get China stock limit-up data status (cn_stock DuckDB)."""
    cn_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cn_stock", "cn_stock.duckdb")
    if not os.path.exists(cn_db):
        return {"error": "cn_stock database not found"}

    conn = duckdb.connect(cn_db, read_only=True)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        result = {"path": cn_db, "tables": {}}
        for (tname,) in tables:
            cnt = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
            result["tables"][tname] = cnt
        return result
    finally:
        conn.close()


# ── Tool registry ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "list_indicators",
        "description": "List all available economic indicators with metadata. "
                       "Optional 'source' param filters by source (cn, us, global_, jp, energy). "
                       "Returns id, name, description, frequency, and last_updated for each indicator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Filter by data source: cn, us, global_, jp, energy"}
            },
        },
    },
    {
        "name": "query_data",
        "description": "Query time-series observations for an economic indicator. "
                       "Requires indicator_id. Supports date range filtering and limit. "
                       "Returns the indicator metadata and a list of date/value observations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "indicator_id": {"type": "integer", "description": "Indicator ID from list_indicators"},
                "start": {"type": "string", "description": "Start date (YYYY-MM-DD), optional"},
                "end": {"type": "string", "description": "End date (YYYY-MM-DD), optional"},
                "limit": {"type": "integer", "description": "Max observations to return, default 100"},
            },
            "required": ["indicator_id"],
        },
    },
    {
        "name": "get_latest",
        "description": "Get the most recent observation for an indicator. Requires indicator_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "indicator_id": {"type": "integer", "description": "Indicator ID from list_indicators"},
            },
            "required": ["indicator_id"],
        },
    },
    {
        "name": "search_indicators",
        "description": "Search indicators by keyword in name or description. "
                       "Useful for finding indicators about specific topics like 'PMI', 'CPI', 'GDP', 'bond', etc.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword (e.g. 'PMI', 'CPI', 'bond')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "data_summary",
        "description": "Get a high-level summary of the entire eco data pipeline: "
                       "total indicators, total observations, breakdown by source and frequency.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "cn_stock_status",
        "description": "Get the status of the China stock limit-up database: available tables and row counts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

TOOL_MAP = {
    "list_indicators": tool_list_indicators,
    "query_data": tool_query_data,
    "get_latest": tool_get_latest,
    "search_indicators": tool_search_indicators,
    "data_summary": tool_data_summary,
    "cn_stock_status": tool_cn_stock_status,
}


# ── MCP JSON-RPC Protocol ─────────────────────────────────────


def _log(msg: str):
    """Write to stderr for debugging (stdout is the MCP transport)."""
    print(f"[eco-data MCP] {msg}", file=sys.stderr, flush=True)


def _send(data: dict):
    """Send a JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


def handle_request(req: dict) -> Optional[dict]:
    """Handle a single JSON-RPC request. Returns response or None for notifications."""
    method = req.get("method", "")
    req_id = req.get("id")

    _log(f"← {method}")

    # ── initialize ──
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "eco-data",
                    "version": "1.0.0",
                },
                "capabilities": {
                    "tools": {},
                },
            },
        }

    # ── notifications (no response) ──
    if method == "notifications/initialized":
        _log("initialized")
        return None
    if method == "notifications/cancelled":
        _log("cancelled")
        return None

    # ── tools/list ──
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    # ── tools/call ──
    if method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in TOOL_MAP:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        try:
            result = TOOL_MAP[tool_name](**tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}
                    ]
                },
            }
        except Exception as e:
            _log(f"tool error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps({"error": str(e)})}
                    ],
                    "isError": True,
                },
            }

    # ── ping ──
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # ── unknown ──
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main():
    _log(f"starting, db={DB_PATH}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            if resp is not None:
                _send(resp)
        except json.JSONDecodeError as e:
            _log(f"JSON parse error: {e}")
        except Exception as e:
            _log(f"unhandled error: {e}")


if __name__ == "__main__":
    main()
