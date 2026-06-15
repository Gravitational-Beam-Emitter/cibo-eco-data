"""
MCP (Model Context Protocol) Server — lightweight JSON-RPC over stdio.

Exposes eco-data tools to AI agents (Claude Code etc.).
Run: python app/mcp_server.py

No external dependencies — pure stdlib JSON-RPC.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

from app.storage import init_db, get_indicators, get_indicator, get_data, search_indicators
from app.pipeline import run_once

SERVER_NAME = "eco-data-mcp"
SERVER_VERSION = "1.0.0"

TOOLS = [
    {
        "name": "list_indicators",
        "description": "List all available macroeconomic indicators. Returns id, source, name, description, frequency, and last_updated for each indicator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Filter by source: cn, us, global_, jp, energy (optional)",
                },
            },
        },
    },
    {
        "name": "get_indicator",
        "description": "Get detailed metadata for a single indicator by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Indicator ID from list_indicators"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "query_data",
        "description": "Query time-series observations for an indicator. Returns date and value pairs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Indicator ID"},
                "start": {"type": "string", "description": "Start date (YYYY-MM-DD, optional)"},
                "end": {"type": "string", "description": "End date (YYYY-MM-DD, optional)"},
                "limit": {"type": "integer", "description": "Max rows to return (default 100)", "default": 100},
            },
            "required": ["id"],
        },
    },
    {
        "name": "search_indicators",
        "description": "Search indicators by keyword in name, description, or source.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword (e.g. 'GDP', 'CPI', 'China')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "trigger_fetch",
        "description": "Trigger a data refresh from upstream sources. Can filter by source.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source to fetch: cn, us, global_, jp, energy (optional, all if omitted)"},
            },
        },
    },
    {
        "name": "get_health",
        "description": "Get database health status — total indicators and observations count.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _log(msg: str) -> None:
    """Log to stderr (stdout is reserved for JSON-RPC)."""
    print(f"[eco-data-mcp] {msg}", file=sys.stderr, flush=True)


# ── Tool handlers ─────────────────────────────────────────────


def handle_list_indicators(args: dict) -> list:
    conn = init_db()
    try:
        source = args.get("source")
        df = get_indicators(conn, source=source)
        result = df.to_dict(orient="records")
        for r in result:
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    r[k] = v.isoformat()
                elif str(type(v)) == "<class 'numpy.int64'>":
                    r[k] = int(v)
        return result
    finally:
        conn.close()


def handle_get_indicator(args: dict) -> dict:
    conn = init_db()
    try:
        row = get_indicator(conn, args["id"])
        if row is None:
            return {"error": f"Indicator {args['id']} not found"}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
            elif str(type(v)) == "<class 'numpy.int64'>":
                row[k] = int(v)
        return row
    finally:
        conn.close()


def handle_query_data(args: dict) -> dict:
    conn = init_db()
    try:
        ind_id = args["id"]
        meta = get_indicator(conn, ind_id)
        if meta is None:
            return {"error": f"Indicator {ind_id} not found"}
        df = get_data(conn, ind_id, start=args.get("start"), end=args.get("end"), limit=args.get("limit", 100))
        records = []
        for _, row in df.iterrows():
            records.append({"date": str(row["date"]), "value": row["value"]})
        return {"indicator": meta["name"], "source": meta["source"], "count": len(records), "data": records}
    finally:
        conn.close()


def handle_search_indicators(args: dict) -> list:
    conn = init_db()
    try:
        df = search_indicators(conn, args["query"])
        result = df.to_dict(orient="records")
        for r in result:
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    r[k] = v.isoformat()
                elif str(type(v)) == "<class 'numpy.int64'>":
                    r[k] = int(v)
        return result
    finally:
        conn.close()


def handle_trigger_fetch(args: dict) -> dict:
    import os
    source = args.get("source")
    summary = run_once(
        fred_api_key=os.environ.get("FRED_API_KEY", ""),
        eia_api_key=os.environ.get("EIA_API_KEY", ""),
        sources=[source] if source else None,
    )
    return summary


def handle_get_health(_args: dict) -> dict:
    conn = init_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
        obs_count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        return {"status": "ok", "indicators": count, "observations": obs_count}
    finally:
        conn.close()


HANDLERS = {
    "list_indicators": handle_list_indicators,
    "get_indicator": handle_get_indicator,
    "query_data": handle_query_data,
    "search_indicators": handle_search_indicators,
    "trigger_fetch": handle_trigger_fetch,
    "get_health": handle_get_health,
}


# ── JSON-RPC ──────────────────────────────────────────────────


def _rpc_response(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _rpc_error(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_request(req: dict) -> Optional[dict]:
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return _rpc_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    if method == "notifications/initialized":
        return None  # no response for notifications

    if method == "tools/list":
        return _rpc_response(req_id, {"tools": TOOLS})

    if method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        handler = HANDLERS.get(tool_name)
        if handler is None:
            return _rpc_error(req_id, -32601, f"Unknown tool: {tool_name}")
        try:
            result = handler(tool_args)
            # Format as MCP tool result
            return _rpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
            })
        except Exception as e:
            return _rpc_error(req_id, -32603, str(e))

    if method == "ping":
        return _rpc_response(req_id, {})

    return _rpc_error(req_id, -32601, f"Unknown method: {method}")


# ── Main loop ─────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server — reads JSON-RPC from stdin, writes to stdout."""
    _log(f"{SERVER_NAME} v{SERVER_VERSION} starting...")
    _log(f"Available tools: {list(HANDLERS.keys())}")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            _log(f"Invalid JSON: {e}")
            continue

        _log(f"<- {req.get('method', '?')}")
        resp = handle_request(req)
        if resp is not None:
            _log(f"-> response (id={resp.get('id')})")
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
