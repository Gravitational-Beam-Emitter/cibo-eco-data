"""
LLM Tagging — Multi-provider LLM integration for stock reason tagging and narrative generation.

Supports: DeepSeek, Anthropic, Qwen (千问), MiniMax — auto-detected from .env keys.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("cn_stock.tagging")

# ── Provider registry ───────────────────────────────────────

# Each provider: (api_style, model, env_var, config_attr)
# api_style: "anthropic" or "openai" (OpenAI-compatible)
PROVIDERS = [
    {
        "name": "deepseek",
        "style": "openai",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "env_var": "DEEPSEEK_API_KEY",
    },
    {
        "name": "anthropic",
        "style": "anthropic",
        "model": "claude-sonnet-4-6",
        "base_url": None,
        "env_var": "ANTHROPIC_API_KEY",
    },
    {
        "name": "qwen",
        "style": "openai",
        "model": "qwen-plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_var": "QWEN_API_KEY",
    },
    {
        "name": "minimax",
        "style": "openai",
        "model": "abab6.5s-chat",
        "base_url": "https://api.minimax.chat/v1",
        "env_var": "MINIMAX_API_KEY",
    },
]


def _get_active_provider() -> Optional[dict]:
    """Return the first provider with a configured API key, or None."""
    from cn_stock import config
    for p in PROVIDERS:
        key = getattr(config, p["env_var"], "")
        if key:
            return {**p, "api_key": key}
    return None


def _call_llm_openai(provider: dict, system_prompt: str, user_prompt: str) -> str:
    """Call an OpenAI-compatible API (DeepSeek, Qwen, MiniMax)."""
    from openai import OpenAI
    client = OpenAI(api_key=provider["api_key"], base_url=provider["base_url"])
    resp = client.chat.completions.create(
        model=provider["model"],
        temperature=0.3,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content or ""


def _call_llm_anthropic(provider: dict, system_prompt: str, user_prompt: str) -> str:
    """Call Anthropic Claude API."""
    from anthropic import Anthropic
    client = Anthropic(api_key=provider["api_key"])
    resp = client.messages.create(
        model=provider["model"],
        max_tokens=4096,
        temperature=0.3,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return resp.content[0].text


def _call_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Route to the first available LLM provider. Returns response text or None."""
    provider = _get_active_provider()
    if not provider:
        logger.warning("No LLM API key configured. Skipping.")
        return None
    try:
        if provider["style"] == "openai":
            text = _call_llm_openai(provider, system_prompt, user_prompt)
        else:
            text = _call_llm_anthropic(provider, system_prompt, user_prompt)
        logger.info(f"LLM call OK via {provider['name']} ({provider['model']})")
        return text
    except Exception as e:
        logger.error(f"LLM call failed ({provider['name']}): {e}")
        return None


def _extract_json(text: str) -> str:
    """Strip markdown code fences from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)
    return text


# ── Stock context builder ───────────────────────────────────

def _build_stock_context(df: pd.DataFrame) -> str:
    """Build a text summary of today's limit-up stocks for the LLM prompt."""
    lines = []
    for _, row in df.iterrows():
        parts = [
            f"{row['code']} {row['name']}",
            f"涨幅{row['pct']:.1f}%",
            f"行业:{row['hybk']}",
            f"连板:{int(row['lbc'])}天" if pd.notna(row.get('lbc')) else "",
            f"封板:{row.get('fbt', '')}" if pd.notna(row.get('fbt')) else "",
            f"炸板:{int(row['zbc'])}次" if pd.notna(row.get('zbc')) and int(row['zbc']) > 0 else "",
            f"封单:{row.get('fund', 0) / 1e8:.1f}亿" if pd.notna(row.get('fund')) else "",
        ]
        lines.append(" | ".join(p for p in parts if p))
    return "\n".join(lines)


# ── Public API ──────────────────────────────────────────────

def tag_stocks(df: pd.DataFrame) -> List[Dict[str, str]]:
    """Generate reason tags for each limit-up stock.

    Returns:
        [{"code": "000768", "reasons": "电子特气+C919大飞机+分红+央企"}, ...]
    """
    if df.empty:
        return []

    context = _build_stock_context(df)
    date = str(df.iloc[0].get("date", "unknown"))[:10]

    system_prompt = "你是一个专业的A股市场分析师，擅长分析涨停板股票的上涨原因。返回严格的JSON格式数据。"
    user_prompt = f"""你是一位A股市场资深分析师。以下是{date}的涨停板股票列表。

请分析每只股票的涨停原因，用3-5个简洁的关键词标签概括，标签之间用"+"连接。

标签要求：
- 优先标注具体的利好事件（如"C919订单"、"新品发布"、"业绩预增"）
- 其次标注炒作概念/板块（如"AI算力"、"低空经济"、"华为产业链"）
- 技术面特征（如"超跌反弹"、"突破新高"、"连板龙头"）
- 公告/消息驱动（如"资产重组"、"分红"、"回购"）
- 每个标签2-6个字，精炼准确
- 风格参考：电子特气项目启动+C919大飞机+分红+央企

以下是当日涨停股信息：
{context}

请返回严格的JSON数组格式，不要包含其他文字：
[{{"code": "股票代码", "reasons": "标签1+标签2+标签3"}}, ...]"""

    text = _call_llm(system_prompt, user_prompt)
    if not text:
        return []

    try:
        result = json.loads(_extract_json(text))
        logger.info(f"LLM tagged {len(result)} stocks")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}\nResponse: {text[:500]}")
        return []


def generate_narratives(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Generate market narratives from the day's limit-up stocks.

    Returns:
        [{"tag": "🤖", "name": "具身智能", "description": "...", "stocks": [...]}, ...]
    """
    if df.empty:
        return []

    industries = df.groupby("hybk").agg(
        count=("code", "count"),
        stocks=("name", lambda x: list(x)[:8]),
        avg_pct=("pct", "mean"),
        max_lbc=("lbc", "max"),
    ).reset_index()

    ind_summary = "\n".join(
        f"- {row['hybk']}: {row['count']}只涨停, "
        f"平均涨幅{row['avg_pct']:.1f}%, "
        f"代表股: {'、'.join(row['stocks'][:5])}"
        for _, row in industries.iterrows()
    )

    lbc_data = df[df["lbc"] >= 2].sort_values("lbc", ascending=False)
    ladder_lines = []
    for lbc_val, group in lbc_data.groupby("lbc"):
        names = "、".join(group["name"].tolist()[:10])
        ladder_lines.append(f"{int(lbc_val)}连板({len(group)}只): {names}")
    ladder_summary = "\n".join(ladder_lines) if ladder_lines else "无2连板以上"

    date = str(df.iloc[0].get("date", "unknown"))[:10]
    total = len(df)

    system_prompt = "你是一个专业的A股市场策略分析师，擅长从涨停板数据中提炼市场主线叙事。返回严格的JSON格式数据。"
    user_prompt = f"""你是一位A股市场策略分析师。以下是{date}涨停板数据：

共{total}只涨停股

【行业分布】
{ind_summary}

【连板梯队】
{ladder_summary}

请从以上涨停股中，归纳出5-10个当日市场主线叙事。每个主线包含：
1. tag: 主线简称（2-4字，如"半导体""AI算力""低空经济"，不用emoji）
2. name: 主线名称（8字以内）
3. description: 2-3句话描述该主线的驱动逻辑和持续性判断
4. stocks: 该主线下的涨停股代码和名称列表（每个含code, name, lbc连板数）

要求：
- 主线要基于实际涨停数据，不要编造
- 优先关注：涨停数量多的行业、有连板龙头的板块、有明显催化剂的概念
- 描述要专业、有洞见，能帮助读者理解市场逻辑

返回严格JSON数组：
[{{"tag": "半导体", "name": "主线名称", "description": "主线描述...", "stocks": [{{"code": "000768", "name": "中航西飞", "lbc": 1}}]}}]"""

    text = _call_llm(system_prompt, user_prompt)
    if not text:
        return []

    try:
        result = json.loads(_extract_json(text))
        logger.info(f"LLM generated {len(result)} narratives")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}\nResponse: {text[:500]}")
        return []


def needs_llm() -> bool:
    """Check if at least one LLM provider is configured."""
    return _get_active_provider() is not None


def active_provider() -> Optional[str]:
    """Return the name of the active LLM provider, or None."""
    p = _get_active_provider()
    return p["name"] if p else None
