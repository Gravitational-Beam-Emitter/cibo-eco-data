"""
Hong Kong SFC (證監會) Enforcement Data Harness.

Fetches enforcement news from the SFC e-Distribution API.
Data includes Chinese + English company/individual names, penalty details.
~2,000 enforcement records, updated daily.

API: POST https://apps.sfc.hk/edistributionWeb/api/news/search
"""

from __future__ import annotations

import logging
import re

import requests

from app.name_matcher import NameMatcher

logger = logging.getLogger("eco_data.hk_sfc")

SFC_API_URL = "https://apps.sfc.hk/edistributionWeb/api/news/search"

# ── Name extraction patterns ─────────────────────────────────────

# Company suffix list for Chinese entity names
_CN_CO_SUFFIX = (
    r"有限公司|股份有限公司|銀行|證券有限公司|保險公司|保險股份有限公司|"
    r"信託公司|期貨公司|資產管理有限公司|集團有限公司|控股有限公司|"
    r"國際有限公司|企業有限公司|財務有限公司|顧問有限公司|融資有限公司|"
    r"資本有限公司|經紀有限公司|代理人有限公司|投資有限公司|金融集團|"
    r"金融控股|證券投資信託股份有限公司|產物保險股份有限公司|"
    r"人壽保險股份有限公司|商業銀行|儲蓄銀行"
)

# English company name: word(s) ending with company type indicator
# Use \b|CJK lookahead as boundary since . in Ltd./Inc. breaks \b before CJK chars
_RE_CO_EN = re.compile(
    r"([A-Z][A-Za-z0-9\s&.()（）,-]+?"
    r"(?:Limited|Ltd\.?|Inc\.?|Corp\.?|Corporation|PLC|LLC|"
    r"Group|Holdings|International|Financial|Securities|Capital|"
    r"Asia|Hong\s+Kong|China|Global|Partners?|Management|"
    r"Services|Trading|Investment|Advisory|Brokerage|"
    r"Securities|Insurance|Futures|Finance))"
    r"(?:\b|(?=[\u4e00-\u9fff（），。；：、]))",
    re.IGNORECASE,
)

# Chinese company name
_RE_CO_CN = re.compile(
    r"([\u4e00-\u9fff（）()A-Za-z0-9]+?(?:" + _CN_CO_SUFFIX + r"))"
)

# Person name at start: "NAME因/在/遭..."
_RE_PERSON_START = re.compile(
    r"^([\u4e00-\u9fff]{2,4})(?:因|在|的|遭|被|及其|為|及其|前)"
)

# Person name after ban/suspension keyword
_RE_PERSON_BAN = re.compile(
    r"(?:禁止|終身禁止|暫時吊銷)\s*([\u4e00-\u9fff]{2,4})"
)

# Penalty amount
_RE_PENALTY_AMT = re.compile(
    r"(?:罰款|罰鍰|罰金|罰|賠償)\s*(?:港幣|港元|HK\$?)?\s*"
    r"([\d,，]+)\s*(?:萬|万|億|亿|元|港元|港幣)?"
)

# Prison sentence
_RE_PRISON = re.compile(
    r"(?:判處|判決|被判)(?:監禁|入獄)\s*([\d]+)\s*(?:個?月|年)"
)

# Combined patterns for company name extraction (used in _extract_primary_name)
_CN_CO_SUFFIX_PAT = (
    r"(?:有限公司|股份有限公司|銀行|證券有限公司|保險股份有限公司|"
    r"保險公司|信託公司|期貨公司|資產管理有限公司|集團有限公司|"
    r"控股有限公司|國際有限公司|企業有限公司|金融集團|"
    r"代理人有限公司|財務有限公司|經紀有限公司|投資有限公司|"
    r"資本有限公司|顧問有限公司|融資有限公司|金融控股有限公司)"
    r"(?:台灣分公司|臺灣分公司|香港分行|香港分公司|國際金融業務分行)?"
)
_CN_CO_BOUNDARY = r"(?:因|在|遭|及其|的|$|，|。|為|違反|被|展開|法律|提出|應|未)"

# Pre-compiled patterns
_CO_AT_START = re.compile(r"^([\u4e00-\u9fff（）()A-Za-z0-9]{2,60}?" + _CN_CO_SUFFIX_PAT + r")" + _CN_CO_BOUNDARY)
_CO_AFTER_TARGET = re.compile(r"針對\s*([\u4e00-\u9fff（）()A-Za-z0-9]{2,60}?" + _CN_CO_SUFFIX_PAT + r")")
_CO_AFTER_AGAINST = re.compile(r"對\s*([\u4e00-\u9fff（）()A-Za-z0-9]{4,60}?" + _CN_CO_SUFFIX_PAT + r")")
_CO_AFTER_WITH = re.compile(r"與\s*([\u4e00-\u9fff（）()A-Za-z0-9]{2,60}?" + _CN_CO_SUFFIX_PAT + r")")
_PERSON_AT_START = re.compile(
    r"^(?:電影製作人|個人投資者|證券欺詐案主腦|前|涉案)?\s*"
    r"([\u4e00-\u9fff]{2,4})(?:因|在|遭|被|及其|為|前|的)"
)
_PERSON_AFTER_BAN = re.compile(r"(?:禁止|終身禁止|暫時吊銷)\s*([\u4e00-\u9fff]{2,4})\s*(?:重投|的牌照|業界|職務)")
_CO_GENERIC = re.compile(
    r"([\u4e00-\u9fff（）()A-Za-z0-9]{3,40}?(?:有限公司|股份有限公司|銀行|"
    r"集團有限公司|控股有限公司|國際有限公司|保險股份有限公司))"
)


def _extract_primary_name(title: str) -> tuple[str, str]:
    """Extract the primary subject name from an SFC enforcement title.

    Returns (name, type) where type is 'entity' or 'individual'.
    """
    # Strategy 1: Company at title start: "NAME因/遭/及其..."
    m = _CO_AT_START.search(title)
    if m:
        name = m.group(1).strip()
        # Reject if name starts with regulator/action keywords
        bad_starts = ("證監會", "金管局", "證監", "香港證監", "法庭", "區域法院")
        if not any(name.startswith(p) for p in bad_starts):
            return name, "entity"

    # Strategy 2: Company after "針對": "證監會取得針對NAME..."
    m = _CO_AFTER_TARGET.search(title)
    if m:
        return m.group(1).strip(), "entity"

    # Strategy 3: Company after "對": "證監會對NAME..."
    m = _CO_AFTER_AGAINST.search(title)
    if m:
        return m.group(1).strip(), "entity"

    # Strategy 4: Company after "與" (co-subject): "證監會與NAME就..."
    m = _CO_AFTER_WITH.search(title)
    if m:
        return m.group(1).strip(), "entity"

    # Strategy 5: English company name
    m = _RE_CO_EN.search(title)
    if m:
        name = m.group(1).strip()
        if len(name) > 4 and not re.match(
            r"^(The|This|That|With|From|About|Under|After|Over|Their|These|There)$",
            name, re.IGNORECASE,
        ):
            return name, "entity"

    # Strategy 6: Person at title start: optionally prefixed by role
    m = _PERSON_AT_START.search(title)
    if m:
        name = m.group(1)
        has_suffix = any(s in name for s in ("有限", "銀行", "證券", "保險", "集團", "控股"))
        if not has_suffix:
            return name, "individual"

    # Strategy 7: Person after ban keyword
    m = _PERSON_AFTER_BAN.search(title)
    if m:
        return m.group(1).strip(), "individual"

    # Strategy 8: Generic Chinese company suffix search (last resort)
    m = _CO_GENERIC.search(title)
    if m:
        name = m.group(1).strip()
        bad_prefixes = ("證監會", "金管局", "根據", "證券及", "香港", "中華人民共和國")
        if len(name) >= 4 and not any(name.startswith(p) for p in bad_prefixes):
            return name, "entity"

    return "", "entity"


def _extract_penalty(title: str) -> str:
    """Extract penalty amount from title."""
    m = _RE_PENALTY_AMT.search(title)
    if m:
        amt = m.group(1).replace(",", "").replace("，", "")
        return f"{amt}万元"

    m = _RE_PRISON.search(title)
    if m:
        return f"监禁{m.group(1)}个月"

    return ""


def _detect_enforcement_type(title: str) -> str:
    """Categorize the enforcement action type."""
    types = []
    if any(kw in title for kw in ("罰款", "罰鍰", "罰金")):
        types.append("fine")
    if "譴責" in title:
        types.append("reprimand")
    if "終身禁止" in title:
        types.append("lifetime_ban")
    elif "禁止" in title:
        types.append("ban")
    if any(kw in title for kw in ("暫時吊銷", "吊銷", "暫停")):
        types.append("suspension")
    if any(kw in title for kw in ("監禁", "判處", "入獄")):
        types.append("prison")
    if "取消資格" in title:
        types.append("disqualification")
    if "凍結" in title:
        types.append("asset_freeze")
    if any(kw in title for kw in ("檢控", "起訴")):
        types.append("prosecution")
    if "賠償" in title:
        types.append("compensation")
    if not types:
        types.append("other")
    return "+".join(types)


def _detect_sector(title: str) -> str:
    """Guess financial sector from title keywords."""
    pairs = [
        ("banking", ("銀行", "Bank")),
        ("insurance", ("保險", "Insurance")),
        ("securities", ("證券", "Securities")),
        ("funds", ("基金", "Fund")),
        ("futures", ("期貨", "Futures")),
        ("virtual_assets", ("虛擬資產", "Virtual Asset", "加密")),
        ("listed_companies", ("上市", "Listed", "IPO")),
        ("brokerage", ("經紀", "Broker")),
    ]
    for sector, keywords in pairs:
        for kw in keywords:
            if kw in title:
                return sector
    return "other_financial"


def fetch_sfc_enforcements() -> list[dict]:
    """Fetch all HK SFC enforcement news via the search API.

    Returns list of structured enforcement records.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36 "
            "EcoData/1.0"
        ),
    })

    all_items = []
    page = 1
    page_size = 100

    logger.info("Fetching HK SFC enforcement news...")

    # Note: SFC API ignores the 'page' parameter — it always returns the first page.
    # We fetch a large pageSize to get as many records as possible in one call.
    # Periodic re-fetching will accumulate historical data via source_uid upsert.
    resp = session.post(SFC_API_URL, json={
        "page": 1,
        "pageSize": 500,
        "sortType": "date-DESC",
        "lang": "TC",
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    all_items = data.get("items", [])
    logger.info(f"Fetched {len(all_items)} items from SFC API (total available: {data.get('total', 0):,})")

    # Filter to enforcement (EF) type only
    all_items = [i for i in all_items if i.get("newsType") == "EF"]

    logger.info(f"Fetched {len(all_items)} SFC enforcement records")

    records = []
    for item in all_items:
        title = item.get("title", "")
        ref_no = item.get("newsRefNo", "")
        issue_date = (item.get("issueDate") or "")[:10]

        name, name_type = _extract_primary_name(title)
        penalty = _extract_penalty(title)
        enf_type = _detect_enforcement_type(title)
        sector = _detect_sector(title)

        notes_parts = [
            f"类型:{enf_type}",
            f"行业:{sector}",
        ]
        if penalty:
            notes_parts.append(f"处罚:{penalty}")
        notes_parts.append(f"来源:HK SFC")
        notes_parts.append(f"文号:{ref_no}")
        notes_parts.append(f"事由:{title[:300]}")

        record = {
            "source": "hk_sfc",
            "source_uid": ref_no,
            "name_en": "",
            "name_cn": name,
            "name_cn_norm": NameMatcher.normalize_cn(name) if name else "",
            "name_pinyin": NameMatcher.to_romanization(NameMatcher.normalize_cn(name)) if name else "",
            "name_type": name_type,
            "pep_level": "",
            "risk_category": "sanctions",
            "aliases": "",
            "programs": "hk_sfc_enforcement",
            "countries": "hk",
            "addresses": "",
            "source_date": issue_date,
            "notes": " | ".join(notes_parts),
            "_sector": sector,
            "_penalty_amount": penalty,
            "_title": title,
        }
        records.append(record)

    return records


def load_hk_sfc_into_screening(db_path: str | None = None) -> int:
    """Fetch HK SFC enforcement data and import into name_screening table."""
    try:
        from app.storage import init_db, upsert_screening_entry
    except ImportError:
        logger.error("Storage module not available")
        return 0

    records = fetch_sfc_enforcements()
    if not records:
        logger.warning("No HK SFC enforcement records fetched")
        return 0

    conn = init_db(db_path)
    count = 0
    for rec in records:
        entry = {
            "source": rec["source"],
            "source_uid": rec["source_uid"],
            "name_en": rec["name_en"],
            "name_cn": rec["name_cn"],
            "name_cn_norm": rec["name_cn_norm"],
            "name_pinyin": rec["name_pinyin"],
            "name_type": rec["name_type"],
            "pep_level": rec["pep_level"],
            "risk_category": rec["risk_category"],
            "aliases": rec["aliases"],
            "programs": rec["programs"],
            "countries": rec["countries"],
            "addresses": rec["addresses"],
            "source_date": rec["source_date"],
            "notes": rec["notes"],
        }
        try:
            upsert_screening_entry(conn, entry)
            count += 1
        except Exception:
            logger.warning(f"Failed to upsert HK SFC entry: {rec['name_cn']}", exc_info=True)

    conn.close()
    logger.info(f"Loaded {count} HK SFC enforcement entries into name_screening")
    return count
