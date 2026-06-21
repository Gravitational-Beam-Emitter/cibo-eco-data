"""
LLM integration — tag Korean stocks with reason labels and generate market narratives.

Reuses the multi-provider pattern from cn_stock/tagging.py (DeepSeek → Anthropic → Qwen → MiniMax).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from kr_stock.config import ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, QWEN_API_KEY, MINIMAX_API_KEY

logger = logging.getLogger("kr_stock.tagging")

PROVIDERS = [
    {"name": "deepseek",  "style": "openai",    "model": "deepseek-chat",
     "base_url": "https://api.deepseek.com", "env_var": "DEEPSEEK_API_KEY"},
    {"name": "anthropic", "style": "anthropic",  "model": "claude-sonnet-4-6",
     "base_url": None, "env_var": "ANTHROPIC_API_KEY"},
    {"name": "qwen",      "style": "openai",    "model": "qwen-plus",
     "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "env_var": "QWEN_API_KEY"},
    {"name": "minimax",   "style": "openai",    "model": "abab6.5s-chat",
     "base_url": "https://api.minimax.chat/v1", "env_var": "MINIMAX_API_KEY"},
]


def _get_active_provider() -> Optional[dict]:
    """Return first provider with a configured API key."""
    for p in PROVIDERS:
        key = os.getenv(p["env_var"], "")
        if key:
            return p
    return None


def _call_llm_openai(provider: dict, system_prompt: str, user_prompt: str) -> str:
    import openai
    client = openai.OpenAI(
        api_key=os.getenv(provider["env_var"]),
        base_url=provider["base_url"],
    )
    resp = client.chat.completions.create(
        model=provider["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )
    return resp.choices[0].message.content or ""


def _call_llm_anthropic(provider: dict, system_prompt: str, user_prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv(provider["env_var"]))
    resp = client.messages.create(
        model=provider["model"],
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.3,
        max_tokens=4096,
    )
    return resp.content[0].text


def _call_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    provider = _get_active_provider()
    if provider is None:
        return None
    try:
        if provider["style"] == "anthropic":
            return _call_llm_anthropic(provider, system_prompt, user_prompt)
        else:
            return _call_llm_openai(provider, system_prompt, user_prompt)
    except Exception as e:
        logger.error(f"LLM call failed ({provider['name']}): {e}")
        return None


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _build_mover_context(df: pd.DataFrame) -> str:
    """Build a text summary of significant movers for the LLM prompt."""
    lines = []
    for _, row in df.iterrows():
        name = row.get("name", "")
        code = row.get("code", "")
        pct = row.get("change_pct", 0)
        sector = row.get("sector", "") or row.get("industry", "")
        market = row.get("market", "")
        vol = row.get("volume", 0)
        direction = "급등" if pct > 0 else "급락"
        line = (f"  {name}({code}) [{market}] {direction} {pct:+.1f}% "
                f"업종={sector} 거래량={vol:,.0f}")
        lines.append(line)
    return "\n".join(lines)


def tag_significant_movers(df: pd.DataFrame) -> List[Dict[str, str]]:
    """Generate reason tags for Korean stocks with significant moves.

    Returns list of {"code": "...", "reasons": "tag1+tag2+tag3"}.
    """
    if df.empty:
        return []

    context = _build_mover_context(df)
    system_prompt = """You are a Korean equity market analyst.
For each stock below, write the main reasons for today's price move.
Use Korean market terminology: sectors like 반도체(semiconductor), 2차전지(batteries),
바이오(biotech), 엔터(entertainment), 플랫폼(platform), 화장품(cosmetics), 방산(defense).

Reasons can include: earnings surprises, analyst upgrades/downgrades, policy catalysts,
foreign buying/selling, sector rotation, supply chain news, geopolitical factors,
M&A rumors, short squeeze, technical breakouts.

Output ONLY valid JSON (no markdown):
[{"code": "005930", "reasons": "reason1+reason2+reason3"}, ...]
Use '+' as separator. 2-4 reasons per stock. Write reasons in English with Korean sector names."""

    user_prompt = f"Tag these Korean stocks with reasons for today's move:\n\n{context}"

    text = _call_llm(system_prompt, user_prompt)
    if not text:
        return []

    try:
        data = json.loads(_extract_json(text))
        return [{"code": d["code"], "reasons": d["reasons"]} for d in data if "code" in d and "reasons" in d]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to parse LLM stock reasons: {e}")
        return []


def generate_market_narratives(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Generate 5-8 Korean market narratives from significant movers.

    Returns list of {"tag": "category", "name": "narrative name",
                      "description": "...", "stocks": [{"code":..., "name":..., "change_pct":...}]}.
    """
    if df.empty:
        return []

    context = _build_mover_context(df)

    # Build industry summary
    if "industry" in df.columns and not df["industry"].isna().all():
        ind_summary = df.groupby("industry").agg(
            count=("code", "count"),
            avg_pct=("change_pct", "mean"),
            top_stocks=("name", lambda x: list(x)[:5])
        ).reset_index()
        ind_lines = []
        for _, r in ind_summary.iterrows():
            ind_lines.append(f"  {r['industry']}: {r['count']}종목, 평균 {r['avg_pct']:+.1f}%")
        context += "\n\n업종별 요약:\n" + "\n".join(ind_lines)

    system_prompt = """You are a Korean equity market strategist at a top Seoul brokerage.
Analyze today's significant stock movers and identify 5-8 market narratives/themes.

A narrative describes WHY a group of stocks moved together — sector rotation, policy catalyst,
global supply chain shift, earnings cycle, foreign inflow theme, etc.

Korean market context:
- Major sectors: 반도체, 2차전지(배터리), 바이오/헬스케어, 인터넷/플랫폼, 화장품, 방산/우주항공, 조선, 엔터테인먼트, 금융, 자동차
- Key drivers: 삼성전자/SK하이닉스 earnings cycle, foreign investor flows, USD/KRW exchange rate,
  US CHIPS Act / IRA policy, China demand, K-콘텐츠 exports, 정부 정책

Each narrative should include:
- tag: short category in Korean or English (e.g., "반도체", "2차전지", "K-방산")
- name: punchy title combining theme + direction
- description: 2-3 sentences explaining the move and its context
- stocks: list of 3-8 representative stocks with code, name, change_pct

Output ONLY valid JSON array (no markdown):
[{"tag": "...", "name": "...", "description": "...", "stocks": [{"code":"...", "name":"...", "change_pct": N}]}]"""

    user_prompt = f"Identify Korean market narratives from today's movers:\n\n{context}"

    text = _call_llm(system_prompt, user_prompt)
    if not text:
        return []

    try:
        data = json.loads(_extract_json(text))
        result = []
        for item in data:
            if "name" not in item:
                continue
            result.append({
                "tag": item.get("tag", ""),
                "name": item["name"],
                "description": item.get("description", ""),
                "stocks": item.get("stocks", []),
            })
        return result
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse LLM narratives: {e}")
        return []


def needs_llm() -> bool:
    """Check if any LLM provider is configured."""
    return _get_active_provider() is not None


def active_provider() -> Optional[str]:
    """Return name of active provider."""
    p = _get_active_provider()
    return p["name"] if p else None
