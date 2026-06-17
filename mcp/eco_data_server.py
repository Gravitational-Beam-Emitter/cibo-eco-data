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
    """Get a high-level summary of the entire eco data platform:
    total indicators, total observations, breakdown by source with descriptions."""
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
            "sources": [
                {
                    "id": r[0],
                    "label": SOURCE_META.get(r[0], {}).get("label", r[0]),
                    "count": r[1],
                    "description": SOURCE_META.get(r[0], {}).get("description", ""),
                }
                for r in by_source
            ],
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


def tool_data_sources_by_category() -> dict:
    """List all data sources grouped by three categories."""
    from app.categories import DataCategory, sources_by_category, category_label
    result = {}
    for cat in DataCategory:
        srcs = sources_by_category(cat)
        result[cat.value] = {
            "label": category_label(cat),
            "label_en": category_label(cat, en=True),
            "sources": [
                {
                    "id": s,
                    "label": SOURCE_META.get(s, {}).get("label", s),
                    "description": SOURCE_META.get(s, {}).get("description", ""),
                }
                for s in srcs
            ],
        }
    return result


def tool_list_risk_indicators(source: str = "") -> list[dict]:
    """List country risk indicators (AML, sanctions, CPI)."""
    from app.categories import DataCategory, sources_by_category
    conn = _conn()
    try:
        risk_sources = sources_by_category(DataCategory.COUNTRY_RISK)
        if source:
            if source not in risk_sources:
                return [{"error": f"Unknown risk source: {source}. Available: {risk_sources}"}]
            rows = conn.execute(
                "SELECT id, source, name, method, description, frequency, last_updated "
                "FROM indicators WHERE source = ? ORDER BY id",
                [source],
            ).fetchall()
        else:
            placeholders = ",".join(["?"] * len(risk_sources))
            rows = conn.execute(
                f"SELECT id, source, name, method, description, frequency, last_updated "
                f"FROM indicators WHERE source IN ({placeholders}) ORDER BY source, id",
                risk_sources,
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


def tool_list_tags() -> list[dict]:
    """List all tags with indicator counts — browse data by topic without knowing keywords."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT tags FROM indicators WHERE tags IS NOT NULL AND tags != ''"
        ).fetchall()
        tag_counts: dict[str, int] = {}
        for (tag_str,) in rows:
            for t in tag_str.split(","):
                t = t.strip()
                if t:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
        return sorted(
            [{"tag": tag, "count": count} for tag, count in tag_counts.items()],
            key=lambda x: x["count"], reverse=True
        )
    finally:
        conn.close()


def tool_search_name(query: str, include_news: bool = False) -> dict:
    """Comprehensive name screening against sanctions, PEP, news, and court records."""
    from app.eco_harness.name_screening import NameScreeningHarness
    nsh = NameScreeningHarness()
    return nsh.screen(query, include_news=include_news)


def tool_name_screening_stats() -> dict:
    """Get name screening database statistics."""
    from app.eco_harness.name_screening import NameScreeningHarness
    nsh = NameScreeningHarness()
    return nsh.get_stats()


# ── Source metadata ──────────────────────────────────────────────

SOURCE_META = {
    "us":   {"label": "US / FRED",              "provider": "Federal Reserve Economic Data", "key_required": True,  "description": "US GDP, CPI, unemployment, Fed funds, Treasury yields, credit spreads, housing, labor, PCE inflation, financial conditions, sovereign yields (8 countries), exchange rates (9 pairs)", "category": "macro"},
    "cn":   {"label": "China / AKShare",        "provider": "AKShare (东方财富/新浪)",        "key_required": False, "description": "中国 GDP, CPI, PPI, PMI, M2, LPR, 社融, 外汇储备, 房地产, 消费, 贸易, 北向资金, 融资融券, 国债收益率, 汇率", "category": "macro"},
    "global_": {"label": "Global / World Bank",  "provider": "World Bank WDI API",            "key_required": False, "description": "GDP, CPI, GDP growth, population for 8+ countries (1960-full)", "category": "macro"},
    "hk":   {"label": "Hong Kong / AKShare",    "provider": "AKShare",                       "key_required": False, "description": "香港 CPI, PPI, GDP, 失业率, 贸易, 建造, HIBOR", "category": "macro"},
    "jp":   {"label": "Japan / BoJ+AKShare",    "provider": "Bank of Japan + AKShare",       "key_required": False, "description": "日本 CPI, 失业率, 政策利率, 领先指标, Tankan调查", "category": "macro"},
    "euro": {"label": "Eurozone / AKShare",     "provider": "AKShare (Jin10财经日历)",       "key_required": False, "description": "欧元区 GDP, CPI, PPI, PMI, 失业率, 工业产出, 零售, 贸易, ZEW/Sentix情绪", "category": "macro"},
    "uk":   {"label": "UK / AKShare",           "provider": "AKShare (Jin10财经日历)",       "key_required": False, "description": "英国 GDP, CPI, 失业率, 零售, 贸易, Halifax/Rightmove房价, 央行利率", "category": "macro"},
    "de":   {"label": "Germany / AKShare",      "provider": "AKShare (Jin10财经日历)",       "key_required": False, "description": "德国 CPI, GDP, Ifo商业景气, ZEW情绪, 贸易", "category": "macro"},
    "au":   {"label": "Australia / AKShare",    "provider": "AKShare (Jin10财经日历)",       "key_required": False, "description": "澳大利亚 CPI, 失业率, 零售, 贸易, RBA利率", "category": "macro"},
    "ca":   {"label": "Canada / AKShare",       "provider": "AKShare (Jin10财经日历)",       "key_required": False, "description": "加拿大 CPI, GDP, 失业率, 贸易, BoC利率", "category": "macro"},
    "ch":   {"label": "Switzerland / AKShare",  "provider": "AKShare (Jin10财经日历)",       "key_required": False, "description": "瑞士 CPI, GDP, 贸易, SVME PMI, SNB利率", "category": "macro"},
    "bond":  {"label": "Bond Market / AKShare",  "provider": "AKShare",                       "key_required": False, "description": "中美各期限国债收益率 (2Y/5Y/10Y/30Y), 利差, 可转债指数", "category": "macro"},
    "futures": {"label": "Futures / AKShare",    "provider": "AKShare (新浪财经)",            "key_required": False, "description": "沪金/沪银/沪铜/螺纹钢/铁矿石/原油主力合约", "category": "macro"},
    "shipping": {"label": "Shipping / AKShare",  "provider": "AKShare (新浪财经)",            "key_required": False, "description": "波罗的海干散货/油轮指数 BDI/BCI/BPI/BCTI", "category": "macro"},
    "banks": {"label": "Central Bank Rates",     "provider": "AKShare (Jin10财经日历)",       "key_required": False, "description": "全球央行政策利率: ECB, BOE, BOJ, RBA, SNB, Fed, RBI, BCB, RBNZ", "category": "macro"},
    "alt":  {"label": "Alternative / Leading",   "provider": "AKShare",                       "key_required": False, "description": "SOX半导体, 原油油轮, 大宗商品/能源/农业/建材指数, 金银ETF持仓, 消费者信心, OPEC产量", "category": "macro"},
    "llm":  {"label": "LLM Ecosystem",           "provider": "GitHub + HuggingFace + PyPI",   "key_required": False, "description": "LLM生态代理指标: GitHub Stars (9 repos), HuggingFace下载量 (5 models), PyPI月下载量 (5 SDKs)", "category": "macro"},
    "defi": {"label": "DeFi & Prediction Markets","provider": "Polymarket + DeFi Llama + CoinGecko", "key_required": False, "description": "链上金融: Polymarket预测市场交易量, DeFi DEX/衍生品TVL, RWA代币化规模, CEX交易量", "category": "macro"},
    "ai":   {"label": "AI Infrastructure",           "provider": "FRED (Federal Reserve Economic Data)", "key_required": True,  "description": "AI全供应链: SOX半导体指数, Kelly数据中心指数, 云计算指数, 半导体/PCB/存储/网络设备/变压器PPI, 制造业建设(芯片fab), 铀/铜/锂价格, 核电发电, 电价, AI机器人指数", "category": "macro"},
    "ai_co": {"label": "AI Company Financials",       "provider": "Yahoo Finance (yfinance)",         "key_required": False, "description": "AI供应链企业财报: NVIDIA/TSMC/ASML/Broadcom营收利润, 微软/亚马逊/谷歌/Meta营收及CapEx, 四大云厂商合计AI基础设施投资", "category": "macro"},
    "cb":  {"label": "A-Share Concept Boards",        "provider": "AKShare (东方财富概念板块)",       "key_required": False, "description": "A股概念板块指数: 光通信/CPO/算力/数据中心/液冷/AI芯片/存储芯片/国产芯片/汽车芯片/半导体/小金属/磷化工/PCB (13个板块)", "category": "macro"},
    "aml":  {"label": "AML/CFT Country Risk Ratings", "provider": "FATF + US State Dept + Basel Institute", "key_required": False, "description": "反洗钱国家风险评级: FATF黑/灰名单(26国), 美国INCSR洗钱关注国(81国), Basel AML指数综合评分(65国)", "category": "country_risk"},
    "sanctions": {"label": "Sanctions & Corruption", "provider": "OFAC + Transparency International", "key_required": False, "description": "制裁与腐败: OFAC SDN制裁名单(19,065实体/个人/船舶/飞行器), 按国家聚合制裁数量, TI腐败感知指数CPI(180国评分排名)", "category": "country_risk"},
    "name_screening": {"label": "Name Screening (中英文)", "provider": "OpenSanctions + GDELT + 阿里云法院", "key_required": False, "description": "名称筛查: OpenSanctions制裁+PEP数据库(440K+实体,含中文名), GDELT全球负面新闻, 阿里云信数科技中国法院涉诉(失信/被执行/裁判文书), 中英文模糊匹配+拼音跨文字搜索", "category": "name_screening"},
    "energy": {"label": "Energy / EIA",          "provider": "U.S. Energy Information Admin", "key_required": True,  "description": "WTI原油价格, Henry Hub天然气价格", "category": "macro"},
}


def tool_data_sources() -> list[dict]:
    """Return metadata for all data sources with categories."""
    return [
        {
            "id": key,
            "label": meta["label"],
            "provider": meta["provider"],
            "key_required": meta["key_required"],
            "category": meta.get("category", "macro"),
            "description": meta["description"],
        }
        for key, meta in SOURCE_META.items()
    ]

TOOLS = [
    {
        "name": "list_indicators",
        "description": "List all available economic indicators with metadata. "
                       "Optional 'source' param filters by source (us, cn, global_, hk, jp, euro, uk, de, au, ca, ch, bond, futures, shipping, banks, alt, llm, defi, energy, ai, ai_co, cb, aml, sanctions, name_screening). "
                       "Returns id, name, description, frequency, and last_updated for each indicator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Filter by data source"}
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
        "name": "data_sources",
        "description": "List all 25 data sources with metadata: provider, whether an API key is required, and description of what data each source provides. Use this to understand the full scope of available data before drilling into specific indicators.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "cn_stock_status",
        "description": "Get the status of the China stock limit-up database: available tables and row counts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_name",
        "description": "Comprehensive name screening against sanctions lists, PEP database, negative news, and Chinese court records. Supports both Chinese (中文) and English names with fuzzy matching and cross-script search (Chinese→Pinyin→English and vice versa). Returns matches categorized by risk: sanctions, PEP, and other. Optionally includes negative news from GDELT and Chinese court records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Name to screen (Chinese or English)"},
                "include_news": {"type": "boolean", "description": "Also search GDELT for negative news (default false)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "name_screening_stats",
        "description": "Get name screening database statistics: total records, breakdown by source and risk category, PEP count, Chinese name coverage.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_tags",
        "description": "List all tags with indicator counts. Browse data by topic (通胀, 就业, AI算力, 数据中心, DeFi...) without knowing exact keywords. Use this to discover available data categories, then use list_indicators with a tag filter or search_indicators to drill down.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "data_sources_by_category",
        "description": "List all data sources grouped by three categories: macro (22 sources: US, China, Eurozone, Japan, A-share concept boards, etc.), country_risk (AML ratings, sanctions, CPI), and name_screening (OpenSanctions PEP/sanctions database, Chinese+English fuzzy search). Use for a structured overview of the platform.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_risk_indicators",
        "description": "List all country risk indicators — AML/CFT ratings (FATF, INCSR, Basel), sanctions (OFAC SDN by country), and corruption perception (TI CPI). Optional 'source' param filters by aml or sanctions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Filter by risk source: aml or sanctions (optional)"},
            },
        },
    },
]

TOOL_MAP = {
    "list_indicators": tool_list_indicators,
    "query_data": tool_query_data,
    "get_latest": tool_get_latest,
    "search_indicators": tool_search_indicators,
    "data_summary": tool_data_summary,
    "data_sources": tool_data_sources,
    "cn_stock_status": tool_cn_stock_status,
    "search_name": tool_search_name,
    "name_screening_stats": tool_name_screening_stats,
    "list_tags": tool_list_tags,
    "data_sources_by_category": tool_data_sources_by_category,
    "list_risk_indicators": tool_list_risk_indicators,
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
                    "version": "1.2.0",
                    "description": "Global economic intelligence platform — three data tiers: "
                                   "MACRO (22 sources: US/FRED, China/AKShare, Eurozone, UK, Germany, Japan, "
                                   "Australia, Canada, Switzerland, Hong Kong, World Bank, bond & futures, "
                                   "shipping, central bank rates, alternative, LLM ecosystem, DeFi, energy/EIA, "
                                   "AI infrastructure, AI company financials, A-share concept boards), "
                                   "COUNTRY RISK (FATF/INCSR/Basel AML ratings, OFAC sanctions, TI CPI), "
                                   "NAME SCREENING (OpenSanctions 383K entities, Chinese+English fuzzy search). "
                                   "Use data_sources_by_category for structured overview, data_summary or "
                                   "data_sources for details, then list_indicators to browse.",
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
